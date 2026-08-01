"""Test token budget enforcement."""
import pytest
from workhorse.token_budget import TokenBudget, TokenBudgetExceeded


def test_budget_check():
    budget = TokenBudget(limit=10000, planning_reserve=500, delivery_reserve=500)
    assert budget.execution_budget == 9000
    assert budget.check(1000) is True


def test_budget_consume():
    budget = TokenBudget(limit=10000, planning_reserve=500, delivery_reserve=500)
    budget.consume(1000)
    assert budget.used == 1000
    assert budget.remaining() == 8000


def test_budget_exceeded():
    budget = TokenBudget(limit=1000, planning_reserve=100, delivery_reserve=100)
    with pytest.raises(TokenBudgetExceeded):
        budget.check(900)
