# Getting started

## Prerequisites

For the Rust CLI:

- Rust 1.70 or newer, including Cargo.
- A supported shell. No network access is required for `providers` or `doctor`.

For the Python compatibility runtime:

- Python 3.9 or newer.
- A Groq API key for `plan`, `exec`, and `run`.

## Install the Rust CLI

From a checkout:

```bash
cargo install --path .
workhorse --version
```

List the provider registry:

```bash
workhorse providers
```

Check which credentials are present. The check reads environment variable names only and does not send a request:

```bash
export OPENAI_API_KEY="replace-me"
workhorse doctor
```

Never put a real credential in shell history, a committed file, a VHS tape, or an issue. Use your CI secret store for automation.

## Use the Python compatibility runtime

Create an isolated environment and install the package:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
export GROQ_API_KEY="replace-me"
```

Run a task directly:

```bash
workhorse-legacy run "inspect the repository and report failing tests"
```

Or separate planning from execution:

```bash
workhorse-legacy plan "inspect the repository and report failing tests" > plan.json
workhorse-legacy exec plan.json
```

The Python runtime stores its append-only ledger at `~/.workhorse/ledger.jsonl` by default. See the configuration example below.

## Python configuration

Set `WORKHORSE_CONFIG` or pass `--config` to the CLI:

```yaml
groq:
  api_key: ""
  model: "llama-3.3-70b-versatile"
  base_url: "https://api.groq.com"
  context_window: 128000
  planning_reserve: 5000
  delivery_reserve: 3000
  temperature: 0.0

execution:
  max_parallel: 8
  timeout: 300
  retry_count: 1
  fail_fast: true
  shell_allowlist: ["cat", "date", "echo", "find", "git", "grep", "ls", "pwd", "pytest", "whoami"]
  allow_shell_operators: false

ledger:
  path: "~/.workhorse/ledger.jsonl"
  archive_path: "~/.workhorse/archive/"
  compaction_threshold: 0.90
```

The environment variable `GROQ_API_KEY` takes effect when `groq.api_key` is omitted. Keep credentials out of this file unless the file is protected by your secret-management policy. Shell execution is restricted to the configured allowlist and does not invoke a shell by default.
