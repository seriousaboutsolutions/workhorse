"""Workhorse CLI. Zero chatter."""
import json
import logging
import sys
from pathlib import Path

import click

from .config import Config
from .deliverer import Deliverer
from .executor import Executor
from .groq_client import GroqClient
from .ledger import Ledger
from .planner import Planner
from .token_budget import TokenBudget

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.WARNING,
)


@click.group()
@click.option("--config", "-c", default=None, help="Path to config file")
@click.pass_context
def main(ctx, config):
    """workhorse: Groq-powered task execution engine."""
    cfg = Config.load(config)
    if not cfg.groq.api_key:
        click.echo("Error: GROQ_API_KEY not set. Export it or add to config.", err=True)
        sys.exit(1)
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg


@main.command()
@click.argument("objective")
@click.pass_context
def plan(ctx, objective):
    """Generate a task plan without executing."""
    cfg = ctx.obj["config"]
    client = GroqClient(cfg.groq)
    planner = Planner(client)
    budget = TokenBudget(
        limit=cfg.groq.context_window,
        planning_reserve=cfg.groq.planning_reserve,
        delivery_reserve=cfg.groq.delivery_reserve,
    )
    try:
        task_plan = planner.plan(objective, budget)
        click.echo(json.dumps(task_plan.to_dict(), indent=2))
    except Exception as e:
        click.echo(f"Plan failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("plan_file")
@click.pass_context
def exec(ctx, plan_file):
    """Execute a plan from a JSON file."""
    cfg = ctx.obj["config"]
    from .planner import TaskPlan

    with open(plan_file, "r") as f:
        plan_data = json.load(f)
    task_plan = TaskPlan.from_dict(plan_data)

    client = GroqClient(cfg.groq)
    ledger = Ledger(cfg.ledger)
    budget = TokenBudget(
        limit=cfg.groq.context_window,
        planning_reserve=cfg.groq.planning_reserve,
        delivery_reserve=cfg.groq.delivery_reserve,
    )
    executor = Executor(client, ledger, budget)
    results = executor.execute(task_plan)

    deliverer = Deliverer()
    output = deliverer.deliver(task_plan, results)
    click.echo(json.dumps(output, indent=2))


@main.command()
@click.argument("objective")
@click.pass_context
def run(ctx, objective):
    """Plan, execute, and deliver in one shot."""
    cfg = ctx.obj["config"]
    client = GroqClient(cfg.groq)
    planner = Planner(client)
    ledger = Ledger(cfg.ledger)
    budget = TokenBudget(
        limit=cfg.groq.context_window,
        planning_reserve=cfg.groq.planning_reserve,
        delivery_reserve=cfg.groq.delivery_reserve,
    )

    task_plan = planner.plan(objective, budget)
    executor = Executor(client, ledger, budget)
    results = executor.execute(task_plan)

    deliverer = Deliverer()
    output = deliverer.deliver(task_plan, results)
    click.echo(json.dumps(output, indent=2))


@main.command()
@click.argument("task_id")
@click.pass_context
def status(ctx, task_id):
    """Get task status from ledger."""
    cfg = ctx.obj["config"]
    ledger = Ledger(cfg.ledger)
    state = ledger.get_task_state(task_id)
    click.echo(json.dumps(state, indent=2))


@main.command()
@click.pass_context
def ledger_tail(ctx):
    """Tail the ledger."""
    cfg = ctx.obj["config"]
    ledger = Ledger(cfg.ledger)
    entries = ledger.get_entries()
    for entry in entries[-20:]:
        click.echo(json.dumps(entry))


if __name__ == "__main__":
    main()
