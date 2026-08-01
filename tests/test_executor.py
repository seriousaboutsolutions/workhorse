"""Test executor with local tools."""
from workhorse.executor import Executor, ExecutionResult
from workhorse.ledger import Ledger
from workhorse.config import ExecutionConfig, LedgerConfig
from workhorse.token_budget import TokenBudget
from workhorse.planner import Step, TaskPlan
from unittest.mock import MagicMock
import tempfile


def test_file_read_tool():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)
        budget = TokenBudget()
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        # Create a test file
        from pathlib import Path
        test_file = Path(tmp) / "test.txt"
        test_file.write_text("hello world")

        result = executor.execute_file_read({"path": str(test_file)}, "t1")
        assert result.status == "success"
        assert result.output == "hello world"


def test_shell_tool():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)
        budget = TokenBudget()
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        result = executor.execute_shell({"command": "echo hello"}, "t1")
        assert result.status == "success"
        assert "hello" in result.output


def test_shell_tool_failure():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)
        budget = TokenBudget()
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        result = executor.execute_shell({"command": "exit 1"}, "t1")
        assert result.status == "failed"
        assert result.exit_code == 1


def test_shell_rejects_operators_and_unapproved_commands():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        executor = Executor(client=MagicMock(), ledger=Ledger(config), budget=TokenBudget())

        chained = executor.execute_shell({"command": "echo safe; pwd"}, "t1")
        unknown = executor.execute_shell({"command": "rm -rf /tmp/example"}, "t1")

        assert chained.status == "failed"
        assert "operators" in chained.error
        assert unknown.status == "failed"
        assert "allowlist" in unknown.error


def test_retry_success_allows_dependents_to_run():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        executor = Executor(
            client=MagicMock(),
            ledger=Ledger(config),
            budget=TokenBudget(),
            execution=ExecutionConfig(retry_count=1),
        )
        attempts = {"1": 0}

        def fake_step(step, task_id):
            if step.id == "1":
                attempts["1"] += 1
                if attempts["1"] == 1:
                    return ExecutionResult(step.id, "failed", error="transient", exit_code=1)
            return ExecutionResult(step.id, "success", output=step.id)

        executor._execute_step = fake_step
        plan = TaskPlan(
            task_id="retry-test",
            objective="retry before dependent execution",
            steps=[
                Step(id="1", action="shell", target="echo one", args={}),
                Step(id="2", action="shell", target="echo two", args={}, depends_on=["1"]),
            ],
            success_criteria="both succeed",
            abort_conditions="none",
            estimated_tokens=10,
        )

        results = executor.execute(plan)

        assert [result.status for result in results] == ["success", "success"]
        assert attempts["1"] == 2


def test_task_execution():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)
        budget = TokenBudget()
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        from pathlib import Path
        test_file = Path(tmp) / "test.txt"
        test_file.write_text("hello world")

        plan = TaskPlan(
            task_id="t1",
            objective="Read file",
            steps=[
                Step(id="1", action="file_read", target=str(test_file), args={"path": str(test_file)}, expected_output="hello world"),
            ],
            success_criteria="file read",
            abort_conditions="none",
            estimated_tokens=100,
        )
        results = executor.execute(plan)
        assert len(results) == 1
        assert results[0].status == "success"
        assert results[0].output == "hello world"
