# workhorse

A Groq-powered task execution engine that prioritizes task-based execution over conversational overhead, minimizes redundant context re-summarization, and delivers higher-quality outputs.

## Core Philosophy

- **Zero Chatter**: No acknowledgements, no status updates, no apologies
- **Task-Based Execution**: Structured planning → silent batch execution → minimal delivery
- **Append-Only Context**: Never re-summarize; split tasks instead
- **Token Budget Enforcement**: Every token is accounted for; tasks split when budgets exceed

## Quick Start

```bash
pip install -e .
workhorse plan "your task here"
workhorse exec <plan_id>
workhorse run "your task here"  # plan + exec + deliver in one shot
```

## Configuration

Create `~/.workhorse/config.yaml`:

```yaml
groq:
  api_key: "your-groq-api-key"
  model: "llama-3.3-70b-versatile"
  base_url: "https://api.groq.com/openai/v1"
  max_tokens: 128000

execution:
  max_parallel: 8
  timeout: 300
  retry_count: 1

ledger:
  path: "~/.workhorse/ledger.jsonl"
  compaction_threshold: 0.9
```
