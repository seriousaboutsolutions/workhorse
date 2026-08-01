"""Policy-controlled executor with dependency-aware retries."""
import hashlib
import logging
import os
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ExecutionConfig
from .groq_client import GroqClient
from .ledger import Ledger
from .planner import Step, TaskPlan
from .token_budget import TokenBudget

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Minimal execution result. No prose."""

    def __init__(self, step_id: str, status: str, output: Optional[str] = None, error: Optional[str] = None, exit_code: int = 0, error_code: Optional[str] = None):
        self.step_id = step_id
        self.status = status
        self.output = output
        self.error = error
        self.exit_code = exit_code
        self.error_code = error_code

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "error_code": self.error_code,
        }


class Executor:
    """Execute task plans with bounded parallelism and an explicit shell policy."""

    TOOL_REGISTRY = {
        "shell": "execute_shell",
        "file_read": "execute_file_read",
        "file_edit": "execute_file_edit",
        "file_write": "execute_file_write",
        "web_search": "execute_web_search",
        "web_fetch": "execute_web_fetch",
    }
    SHELL_ALIASES = {
        "ls": "ls", "cat": "cat", "grep": "grep", "find": "find", "mkdir": "mkdir",
        "rm": "rm", "cp": "cp", "mv": "mv", "pwd": "pwd", "whoami": "whoami",
        "date": "date", "git": "git", "python": "python3", "pip": "pip", "npm": "npm",
        "node": "node", "make": "make", "docker": "docker", "kubectl": "kubectl",
        "terraform": "terraform", "ansible": "ansible", "pytest": "pytest",
    }
    SHELL_OPERATORS = {"|", "||", "&", "&&", ";", ">", ">>", "<", "<<"}
    SHELL_OPERATOR_CHARS = set("|&;><")

    def __init__(
        self,
        client: GroqClient,
        ledger: Ledger,
        budget: TokenBudget,
        execution: Optional[ExecutionConfig] = None,
    ):
        self.client = client
        self.ledger = ledger
        self.budget = budget
        self.execution = execution or ExecutionConfig(workspace_root=None)
        self.workspace_root = (
            Path(self.execution.workspace_root).expanduser().resolve()
            if self.execution.workspace_root else None
        )

    def execute(self, plan: TaskPlan) -> List[ExecutionResult]:
        """Execute a plan in dependency-ready batches."""
        self.ledger.append("plan", task_id=plan.task_id, content=plan.to_dict())
        results: List[ExecutionResult] = []
        pending = {s.id: s for s in plan.steps}
        completed: Dict[str, ExecutionResult] = {}

        while pending:
            ready = [
                step for step in pending.values()
                if not step.depends_on or all(dependency in completed for dependency in step.depends_on)
            ]
            if not ready:
                logger.error("Circular or unresolved dependency detected in plan")
                for step in pending.values():
                    completed[step.id] = ExecutionResult(step.id, "failed", error="Unresolved dependency graph", exit_code=1)
                    results.append(completed[step.id])
                break

            runnable: List[Step] = []
            for step in ready:
                failed_dependencies = [
                    dependency for dependency in step.depends_on
                    if completed[dependency].status != "success"
                ]
                if failed_dependencies:
                    result = ExecutionResult(
                        step.id,
                        "failed",
                        error=f"Aborted: dependency failed ({', '.join(failed_dependencies)})",
                        exit_code=1,
                    )
                    completed[step.id] = result
                    results.append(result)
                else:
                    runnable.append(step)

            for step, result in zip(runnable, self._execute_batch(runnable, plan.task_id)):
                completed[step.id] = result
                results.append(result)

            for step in ready:
                pending.pop(step.id, None)

            failed_batch = [result for result in results[-len(ready):] if result.status == "failed"]
            if failed_batch and self.execution.fail_fast and pending:
                failure = failed_batch[0]
                for step in list(pending.values()):
                    result = ExecutionResult(
                        step.id,
                        "failed",
                        error=f"Aborted: fail_fast after step {failure.step_id} failed",
                        exit_code=1,
                    )
                    completed[step.id] = result
                    results.append(result)
                    pending.pop(step.id)
                break

        return results

    def _execute_batch(self, steps: List[Step], task_id: str) -> List[ExecutionResult]:
        """Execute independent steps concurrently, preserving plan order."""
        workers = max(1, min(self.execution.max_parallel, len(steps)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(self._execute_with_retries, step, task_id) for step in steps]
            return [future.result() for future in futures]

    def _execute_with_retries(self, step: Step, task_id: str) -> ExecutionResult:
        attempts = max(1, step.retries + 1, self.execution.retry_count + 1)
        result = self._execute_step(step, task_id)
        for attempt in range(1, attempts):
            if result.status == "success":
                break
            logger.info("Retrying step %s (%s/%s)", step.id, attempt, attempts - 1)
            result = self._execute_step(step, task_id)
        return result

    def _execute_step(self, step: Step, task_id: str) -> ExecutionResult:
        handler = getattr(self, self.TOOL_REGISTRY.get(step.action, ""), None)
        if not handler and step.action in self.SHELL_ALIASES:
            command = self.SHELL_ALIASES[step.action]
            if step.target:
                command += f" {shlex.quote(step.target)}"
            for key, value in step.args.items():
                command += f" {key} {shlex.quote(str(value))}"
            handler = self.execute_shell
            args = {"command": command}
        elif handler:
            args = step.args
        else:
            return ExecutionResult(step.id, "failed", error=f"Unknown tool: {step.action}", exit_code=1)

        start = time.time()
        try:
            result = handler(args, task_id)
            elapsed = time.time() - start
            result.step_id = step.id
            self.ledger.append(
                "tool_call", task_id=task_id, step_id=step.id, action=step.action,
                status=result.status, output_hash=self._hash(result.output or ""), elapsed=round(elapsed, 3),
            )
            return result
        except Exception as error:
            elapsed = time.time() - start
            self.ledger.append(
                "tool_call", task_id=task_id, step_id=step.id, action=step.action,
                status="failed", error=str(error), elapsed=round(elapsed, 3),
            )
            return ExecutionResult(step.id, "failed", error=str(error), exit_code=1)

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _workspace_path(self, raw_path: str) -> tuple[Optional[Path], Optional[str]]:
        path = Path(raw_path).expanduser()
        if not path.is_absolute() and self.workspace_root:
            path = self.workspace_root / path
        resolved = path.resolve(strict=False)
        if self.workspace_root and resolved != self.workspace_root and self.workspace_root not in resolved.parents:
            return None, f"Path is outside workspace root: {resolved}"
        return resolved, None

    def _cwd(self, raw_cwd: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if raw_cwd:
            path, error = self._workspace_path(raw_cwd)
            if error:
                return None, error
            return str(path), None
        return str(self.workspace_root) if self.workspace_root else None, None

    def execute_file_read(self, args: Dict, task_id: str) -> ExecutionResult:
        path, policy_error = self._workspace_path(args.get("path", ""))
        if policy_error:
            return ExecutionResult("", "failed", error=policy_error, exit_code=126, error_code="policy.path_outside_workspace")
        if not path.exists():
            return ExecutionResult("", "failed", error=f"File not found: {path}", exit_code=1)
        return ExecutionResult("", "success", output=path.read_text())

    def execute_file_write(self, args: Dict, task_id: str) -> ExecutionResult:
        path, policy_error = self._workspace_path(args.get("path", ""))
        if policy_error:
            return ExecutionResult("", "failed", error=policy_error, exit_code=126, error_code="policy.path_outside_workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content", ""))
        return ExecutionResult("", "success", output=f"Wrote {path}")

    def execute_file_edit(self, args: Dict, task_id: str) -> ExecutionResult:
        path, policy_error = self._workspace_path(args.get("path", ""))
        if policy_error:
            return ExecutionResult("", "failed", error=policy_error, exit_code=126, error_code="policy.path_outside_workspace")
        if not path.exists():
            return ExecutionResult("", "failed", error=f"File not found: {path}", exit_code=1)
        content = path.read_text()
        old = args.get("old", "")
        if old not in content:
            return ExecutionResult("", "failed", error=f"Old string not found in {path}", exit_code=1)
        path.write_text(content.replace(old, args.get("new", ""), args.get("count", 1)))
        return ExecutionResult("", "success", output=f"Edited {path}")

    def _command_args(self, command: str) -> tuple[Optional[List[str]], Optional[str]]:
        try:
            argv = shlex.split(command)
        except ValueError as error:
            return None, f"Invalid command syntax: {error}"
        if not argv:
            return None, "Command is empty"
        if not self.execution.allow_shell_operators and any(
            token in self.SHELL_OPERATORS or any(character in token for character in self.SHELL_OPERATOR_CHARS)
            for token in argv
        ):
            return None, "policy.shell_operators: shell operators are disabled; use separate plan steps"
        executable = os.path.basename(argv[0])
        allowed = set(self.execution.shell_allowlist)
        if executable == "exit":
            return argv, None
        if executable not in allowed:
            return None, f"policy.command_not_allowed: command '{executable}' is not in the shell allowlist"
        return argv, None

    def execute_shell(self, args: Dict, task_id: str) -> ExecutionResult:
        """Execute an allowlisted process, or an explicit unsafe shell command."""
        command = str(args.get("command", ""))
        timeout = min(float(args.get("timeout", self.execution.timeout)), self.execution.timeout)
        cwd, cwd_error = self._cwd(args.get("cwd"))
        if cwd_error:
            return ExecutionResult("", "failed", error=cwd_error, exit_code=126, error_code="policy.path_outside_workspace")
        if self.execution.allow_shell_operators:
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=timeout,
                    cwd=cwd,
                )
                return ExecutionResult(
                    "", "success" if result.returncode == 0 else "failed", output=result.stdout,
                    error=result.stderr, exit_code=result.returncode,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult("", "failed", error=f"Timeout after {timeout}s", exit_code=124)

        argv, error = self._command_args(command)
        if error:
            error_code = "policy.command_not_allowed" if error.startswith("policy.") else "policy.invalid_command"
            return ExecutionResult("", "failed", error=error, exit_code=126, error_code=error_code)
        if argv[0] == "exit":
            code = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 0
            return ExecutionResult("", "failed" if code else "success", exit_code=code)
        try:
            result = subprocess.run(
                argv, shell=False, capture_output=True, text=True, timeout=timeout,
                cwd=cwd,
            )
            return ExecutionResult(
                "", "success" if result.returncode == 0 else "failed", output=result.stdout,
                error=result.stderr, exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult("", "failed", error=f"Timeout after {timeout}s", exit_code=124)
        except OSError as error:
            return ExecutionResult("", "failed", error=str(error), exit_code=127)

    def execute_web_search(self, args: Dict, task_id: str) -> ExecutionResult:
        return ExecutionResult("", "failed", error="Web search not implemented", exit_code=1)

    def execute_web_fetch(self, args: Dict, task_id: str) -> ExecutionResult:
        import urllib.request
        try:
            with urllib.request.urlopen(args.get("url", ""), timeout=self.execution.timeout) as response:
                return ExecutionResult("", "success", output=response.read().decode("utf-8", errors="replace"))
        except Exception as error:
            return ExecutionResult("", "failed", error=str(error), exit_code=1)
