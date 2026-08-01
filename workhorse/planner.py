"""Task planner with structured output and ambiguity resolution."""
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .groq_client import GroqClient
from .token_budget import TokenBudget

logger = logging.getLogger(__name__)


@dataclass
class Step:
    id: str
    action: str
    target: str
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    expected_output: str = ""
    retries: int = 1
    status: str = "pending"
    result: Optional[Dict] = None


@dataclass
class TaskPlan:
    task_id: str
    objective: str
    steps: List[Step]
    success_criteria: str
    abort_conditions: str
    estimated_tokens: int
    verification_command: Optional[str] = None
    output_format: str = "json"

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "steps": [
                {
                    "id": s.id,
                    "action": s.action,
                    "target": s.target,
                    "args": s.args,
                    "depends_on": s.depends_on,
                    "expected_output": s.expected_output,
                    "retries": s.retries,
                    "status": s.status,
                }
                for s in self.steps
            ],
            "success_criteria": self.success_criteria,
            "abort_conditions": self.abort_conditions,
            "estimated_tokens": self.estimated_tokens,
            "verification_command": self.verification_command,
            "output_format": self.output_format,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskPlan":
        steps = [Step(**s) for s in data.get("steps", [])]
        return cls(
            task_id=data["task_id"],
            objective=data["objective"],
            steps=steps,
            success_criteria=data["success_criteria"],
            abort_conditions=data["abort_conditions"],
            estimated_tokens=data["estimated_tokens"],
            verification_command=data.get("verification_command"),
            output_format=data.get("output_format", "json"),
        )


class Planner:
    """Generates structured task plans from user intent."""

    PLAN_PROMPT = """You are a task planner. Decompose the user's objective into a structured execution plan.

Output strictly in this JSON format (no markdown, no prose):
{
  "objective": "one-sentence goal",
  "steps": [
    {
      "id": "1",
      "action": "tool_name",
      "target": "file_path_or_url",
      "args": {"key": "value"},
      "depends_on": [],
      "expected_output": "what this step produces",
      "retries": 1
    }
  ],
  "success_criteria": "measurable success condition",
  "abort_conditions": "max retries, timeout, specific errors",
  "estimated_tokens": 15000,
  "verification_command": "optional test command",
  "output_format": "json"
}

Rules:
- Steps with empty depends_on can run in parallel
- All file paths must be resolved
- estimated_tokens is total for all steps
- No extra text outside the JSON"""

    def __init__(self, client: GroqClient):
        self.client = client

    def plan(self, objective: str, budget: TokenBudget) -> TaskPlan:
        """Generate a task plan from an objective."""
        estimated = self.client.estimate_tokens(objective + self.PLAN_PROMPT)
        budget.check(estimated)

        messages = [
            {"role": "system", "content": self.PLAN_PROMPT},
            {"role": "user", "content": objective},
        ]
        response = self.client.chat(
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response["content"]
        budget.consume(response["usage"]["total_tokens"])

        try:
            plan_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            raise

        plan_data["task_id"] = str(uuid.uuid4())[:8]
        plan = TaskPlan.from_dict(plan_data)

        budget.check(plan.estimated_tokens)
        logger.info(f"Plan generated: {plan.task_id} ({len(plan.steps)} steps, {plan.estimated_tokens} est. tokens)")
        return plan

    def validate(self, plan: TaskPlan, budget: TokenBudget) -> bool:
        """Validate a plan against constraints."""
        try:
            budget.check(plan.estimated_tokens)
            return True
        except Exception as e:
            logger.warning(f"Plan validation failed: {e}")
            return False
