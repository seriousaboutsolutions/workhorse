"""End-to-end integration test for workhorse."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from workhorse.config import Config, LedgerConfig
from workhorse.deliverer import Deliverer
from workhorse.executor import Executor
from workhorse.groq_client import GroqClient
from workhorse.ledger import Ledger
from workhorse.planner import Planner, TaskPlan, Step
from workhorse.token_budget import TokenBudget


def test_end_to_end_plan_execute():
    """Plan a task and execute it locally."""
    with tempfile.TemporaryDirectory() as tmp:
        # Setup
        config = Config(
            groq=Config().groq,
            ledger=LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/"),
        )
        ledger = Ledger(config.ledger)
        budget = TokenBudget(
            limit=config.groq.context_window,
            planning_reserve=config.groq.planning_reserve,
            delivery_reserve=config.groq.delivery_reserve,
        )
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        # Create a test file
        test_file = Path(tmp) / "test.txt"
        test_file.write_text("hello world")

        # Define plan manually (simulating planner output)
        plan = TaskPlan(
            task_id="e2e-test",
            objective="Read test file and run shell command",
            steps=[
                Step(
                    id="1",
                    action="file_read",
                    target=str(test_file),
                    args={"path": str(test_file)},
                    expected_output="hello world",
                ),
                Step(
                    id="2",
                    action="shell",
                    target="echo hello",
                    args={"command": "echo hello"},
                    depends_on=["1"],
                    expected_output="hello",
                ),
            ],
            success_criteria="both steps succeed",
            abort_conditions="none",
            estimated_tokens=200,
        )

        # Execute
        results = executor.execute(plan)
        assert len(results) == 2
        assert results[0].status == "success"
        assert results[0].output == "hello world"
        assert results[1].status == "success"
        assert "hello" in results[1].output

        # Deliver
        deliverer = Deliverer()
        output = deliverer.deliver(plan, results)
        assert output["status"] == "success"
        assert output["summary"]["success"] == 2

        # Verify ledger
        state = ledger.get_task_state("e2e-test")
        assert state["total_entries"] >= 3  # plan + 2 tool calls


def test_parallel_execution():
    """Execute independent steps in parallel."""
    with tempfile.TemporaryDirectory() as tmp:
        config = Config(
            ledger=LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/"),
        )
        ledger = Ledger(config.ledger)
        budget = TokenBudget()
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        plan = TaskPlan(
            task_id="parallel-test",
            objective="Run two shell commands in parallel",
            steps=[
                Step(id="1", action="shell", target="echo a", args={"command": "echo a"}),
                Step(id="2", action="shell", target="echo b", args={"command": "echo b"}),
            ],
            success_criteria="both succeed",
            abort_conditions="none",
            estimated_tokens=100,
        )
        results = executor.execute(plan)
        assert len(results) == 2
        assert all(r.status == "success" for r in results)


def test_fail_fast():
    """Abort dependent chain on failure."""
    with tempfile.TemporaryDirectory() as tmp:
        config = Config(
            ledger=LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/"),
        )
        ledger = Ledger(config.ledger)
        budget = TokenBudget()
        executor = Executor(client=MagicMock(), ledger=ledger, budget=budget)

        plan = TaskPlan(
            task_id="fail-test",
            objective="Fail step 1, abort step 2",
            steps=[
                Step(id="1", action="shell", target="exit 1", args={"command": "exit 1"}),
                Step(id="2", action="shell", target="echo never", args={"command": "echo never"}, depends_on=["1"]),
            ],
            success_criteria="both succeed",
            abort_conditions="fail fast",
            estimated_tokens=100,
        )
        results = executor.execute(plan)
        assert results[0].status == "failed"
        assert results[1].status == "failed"  # Aborted due to dependency
        assert "dependency failed" in results[1].error or "Aborted" in results[1].error
