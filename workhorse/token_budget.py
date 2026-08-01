"""Token budget enforcement for workhorse."""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TokenBudgetExceeded(Exception):
    """Raised when a task exceeds the allocated token budget."""
    pass


@dataclass
class TokenBudget:
    limit: int = 128000
    planning_reserve: int = 5000
    delivery_reserve: int = 3000
    used: int = 0

    @property
    def execution_budget(self) -> int:
        return self.limit - self.planning_reserve - self.delivery_reserve

    def check(self, estimated: int) -> bool:
        if self.used + estimated > self.execution_budget:
            raise TokenBudgetExceeded(
                f"Task exceeds budget: {self.used + estimated} > {self.execution_budget}. "
                f"Split into subtasks or escalate."
            )
        return True

    def consume(self, actual: int) -> None:
        self.used += actual
        if self.used > self.execution_budget * 0.8:
            logger.warning(
                f"Token budget 80% consumed: {self.used}/{self.execution_budget}"
            )

    def remaining(self) -> int:
        return self.execution_budget - self.used

    def __repr__(self) -> str:
        return (
            f"TokenBudget(limit={self.limit}, "
            f"execution_budget={self.execution_budget}, "
            f"used={self.used}, remaining={self.remaining()})"
        )
