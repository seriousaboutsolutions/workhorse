"""Silent batched executor with parallel tool calls."""
import asyncio
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional

from .groq_client import GroqClient
from .ledger import Ledger
from .planner import Step, TaskPlan
from .token_budget import TokenBudget

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Minimal execution result. No prose."""

    def __init__(self, step_id: str, status: str, output: Optional[str] = None, error: Optional[str] = None, exit_code: int = 0):
        self.step_id = step_id
        self.status = status
        self.output = output
        self.error = error
        self.exit_code = exit_code

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
        }


class Executor:
    """Executes task plans silently with batching."""

    TOOL_REGISTRY = {
        "shell": "execute_shell",
        "file_read": "execute_file_read",
        "file_edit": "execute_file_edit",
        "file_write": "execute_file_write",
        "web_search": "execute_web_search",
        "web_fetch": "execute_web_fetch",
    }
    # Map common command names to shell equivalents
    SHELL_ALIASES = {
        "ls": "ls",
        "cat": "cat",
        "grep": "grep",
        "find": "find",
        "mkdir": "mkdir",
        "rm": "rm",
        "cp": "cp",
        "mv": "mv",
        "pwd": "pwd",
        "whoami": "whoami",
        "date": "date",
        "git": "git",
        "python": "python3",
        "pip": "pip",
        "npm": "npm",
        "node": "node",
        "make": "make",
        "docker": "docker",
        "kubectl": "kubectl",
        "terraform": "terraform",
        "ansible": "ansible",
        "pytest": "pytest",
    }

    def __init__(self, client: GroqClient, ledger: Ledger, budget: TokenBudget):
        self.client = client
        self.ledger = ledger
        self.budget = budget

    def execute(self, plan: TaskPlan) -> List[ExecutionResult]:
        """Execute a plan with parallel batching."""
        self.ledger.append("plan", task_id=plan.task_id, content=plan.to_dict())
        results: List[ExecutionResult] = []
        pending = {s.id: s for s in plan.steps}
        completed: Dict[str, ExecutionResult] = {}

        while pending:
            ready = [s for s in pending.values() if not s.depends_on or all(d in completed for d in s.depends_on)]
            if not ready:
                logger.error("Circular dependency detected in plan")
                break

            # Execute ready steps in parallel
            batch_results = self._execute_batch(ready, plan.task_id)
            for step, result in zip(ready, batch_results):
                del pending[step.id]
                completed[step.id] = result
                results.append(result)

                if result.status == "failed":
                    # Abort all dependent steps
                    for dep_step in list(pending.values()):
                        if step.id in dep_step.depends_on:
                            dep_result = ExecutionResult(
                                step_id=dep_step.id,
                                status="failed",
                                error=f"Aborted: dependency step {step.id} failed",
                                exit_code=1,
                            )
                            del pending[dep_step.id]
                            completed[dep_step.id] = dep_result
                            results.append(dep_result)

                    if step.retries > 0:
                        # Retry once
                        logger.info(f"Retrying step {step.id}")
                        retry_result = self._execute_step(step, plan.task_id)
                        completed[step.id] = retry_result
                        # Replace the failed result with the retry
                        for i, r in enumerate(results):
                            if r.step_id == step.id and r.error != f"Aborted: dependency step {step.id} failed":
                                results[i] = retry_result
                                break
                        # If retry succeeded, we need to re-add aborted dependents... skip for simplicity
                        # In production, this would be a more complex retry graph

        return results

    def _execute_batch(self, steps: List[Step], task_id: str) -> List[ExecutionResult]:
        """Execute a batch of steps."""
        # Use asyncio for true parallelism if async tools available
        # For now, sequential with minimal overhead
        return [self._execute_step(s, task_id) for s in steps]

    def _execute_step(self, step: Step, task_id: str) -> ExecutionResult:
        """Execute a single step."""
        handler = getattr(self, self.TOOL_REGISTRY.get(step.action, ""), None)
        if not handler:
            # Check if it's a shell alias
            if step.action in self.SHELL_ALIASES:
                command = self.SHELL_ALIASES[step.action]
                if step.target:
                    command += f" {step.target}"
                if step.args:
                    for key, val in step.args.items():
                        command += f" {key} {val}" if not key.startswith("-") else f" {key} {val}"
                handler = self.execute_shell
                step.args = {"command": command.strip()}
            else:
                return ExecutionResult(
                    step_id=step.id,
                    status="failed",
                    error=f"Unknown tool: {step.action}",
                    exit_code=1,
                )

        start = time.time()
        try:
            result = handler(step.args, task_id)
            elapsed = time.time() - start
            result.step_id = step.id
            self.ledger.append(
                "tool_call",
                task_id=task_id,
                step_id=step.id,
                action=step.action,
                status=result.status,
                output_hash=self._hash(result.output or ""),
                elapsed=round(elapsed, 3),
            )
            return result
        except Exception as e:
            elapsed = time.time() - start
            self.ledger.append(
                "tool_call",
                task_id=task_id,
                step_id=step.id,
                action=step.action,
                status="failed",
                error=str(e),
                elapsed=round(elapsed, 3),
            )
            return ExecutionResult(
                step_id=step.id,
                status="failed",
                error=str(e),
                exit_code=1,
            )

    def _hash(self, text: str) -> str:
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def execute_file_read(self, args: Dict, task_id: str) -> ExecutionResult:
        """Read a file."""
        from pathlib import Path
        path = Path(args.get("path", "")).expanduser()
        if not path.exists():
            return ExecutionResult("", "failed", error=f"File not found: {path}", exit_code=1)
        content = path.read_text()
        return ExecutionResult("", "success", output=content)

    def execute_file_write(self, args: Dict, task_id: str) -> ExecutionResult:
        """Write a file."""
        from pathlib import Path
        path = Path(args.get("path", "")).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content", ""))
        return ExecutionResult("", "success", output=f"Wrote {path}")

    def execute_file_edit(self, args: Dict, task_id: str) -> ExecutionResult:
        """Edit a file by replacing a string."""
        from pathlib import Path
        path = Path(args.get("path", "")).expanduser()
        if not path.exists():
            return ExecutionResult("", "failed", error=f"File not found: {path}", exit_code=1)
        content = path.read_text()
        old = args.get("old", "")
        new = args.get("new", "")
        if old not in content:
            return ExecutionResult("", "failed", error=f"Old string not found in {path}", exit_code=1)
        content = content.replace(old, new, args.get("count", 1))
        path.write_text(content)
        return ExecutionResult("", "success", output=f"Edited {path}")

    def execute_shell(self, args: Dict, task_id: str) -> ExecutionResult:
        """Execute a shell command."""
        command = args.get("command", "")
        timeout = args.get("timeout", 300)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=args.get("cwd"),
            )
            return ExecutionResult(
                "",
                "success" if result.returncode == 0 else "failed",
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult("", "failed", error=f"Timeout after {timeout}s", exit_code=124)

    def execute_web_search(self, args: Dict, task_id: str) -> ExecutionResult:
        """Search the web. Placeholder for web search integration."""
        return ExecutionResult("", "failed", error="Web search not implemented", exit_code=1)

    def execute_web_fetch(self, args: Dict, task_id: str) -> ExecutionResult:
        """Fetch a URL."""
        import urllib.request
        url = args.get("url", "")
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read().decode("utf-8", errors="replace")
                return ExecutionResult("", "success", output=content)
        except Exception as e:
            return ExecutionResult("", "failed", error=str(e), exit_code=1)
