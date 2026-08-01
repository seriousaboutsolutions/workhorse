"""Minimal deliverer. No framing, no summaries, no prose."""
import json
import logging
from typing import Any, Dict, List

from .executor import ExecutionResult
from .planner import TaskPlan

logger = logging.getLogger(__name__)


class Deliverer:
    """Deliver results in the exact format requested."""

    def deliver(self, plan: TaskPlan, results: List[ExecutionResult]) -> Dict[str, Any]:
        """Deliver task results in structured format."""
        failed = [r for r in results if r.status == "failed"]
        success = [r for r in results if r.status == "success"]

        if failed and not success:
            status = "failed"
        elif failed and success:
            status = "partial"
        else:
            status = "success"

        output = {
            "task_id": plan.task_id,
            "status": status,
            "objective": plan.objective,
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "success": len(success),
                "failed": len(failed),
            },
        }

        if plan.output_format == "json":
            return output
        elif plan.output_format == "yaml":
            import yaml
            return yaml.safe_dump(output)
        elif plan.output_format == "table":
            return self._format_table(results)
        else:
            return output

    def _format_table(self, results: List[ExecutionResult]) -> str:
        lines = ["| Step | Status | Output | Error |", "|---|---|---|---|"]
        for r in results:
            out = (r.output or "")[:60].replace("|", "\\|")
            err = (r.error or "")[:60].replace("|", "\\|")
            lines.append(f"| {r.step_id} | {r.status} | {out} | {err} |")
        return "\n".join(lines)

    def deliver_error(self, task_id: str, error: str) -> Dict[str, Any]:
        """Deliver an error with minimal framing."""
        return {
            "task_id": task_id,
            "status": "failed",
            "error": error,
        }
