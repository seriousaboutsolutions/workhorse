"""Test planner logic without Groq API."""
import json
from unittest.mock import MagicMock, patch
from workhorse.planner import Planner, TaskPlan
from workhorse.token_budget import TokenBudget


def test_plan_from_dict():
    data = {
        "task_id": "abc123",
        "objective": "Test objective",
        "steps": [
            {
                "id": "1",
                "action": "shell",
                "target": "echo hello",
                "args": {"command": "echo hello"},
                "depends_on": [],
                "expected_output": "hello",
                "retries": 1,
                "status": "pending",
            }
        ],
        "success_criteria": "echo outputs hello",
        "abort_conditions": "3 retries",
        "estimated_tokens": 100,
        "verification_command": None,
        "output_format": "json",
    }
    plan = TaskPlan.from_dict(data)
    assert plan.task_id == "abc123"
    assert len(plan.steps) == 1
    assert plan.steps[0].action == "shell"


def test_plan_to_dict():
    plan = TaskPlan(
        task_id="test",
        objective="test",
        steps=[],
        success_criteria="ok",
        abort_conditions="none",
        estimated_tokens=0,
    )
    d = plan.to_dict()
    assert d["task_id"] == "test"
    assert d["estimated_tokens"] == 0


def test_plan_validation():
    budget = TokenBudget(limit=10000, planning_reserve=500, delivery_reserve=500)
    planner = Planner(client=MagicMock())
    plan = TaskPlan(
        task_id="test",
        objective="test",
        steps=[],
        success_criteria="ok",
        abort_conditions="none",
        estimated_tokens=5000,
    )
    assert planner.validate(plan, budget) is True

    plan.estimated_tokens = 10000
    assert planner.validate(plan, budget) is False
