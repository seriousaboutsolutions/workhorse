# CLI reference

## Rust commands

### `workhorse providers`

Prints the local provider registry: stable ID, display name, environment variable, and base URL. It performs no network requests and does not require credentials.

### `workhorse doctor`

Reports provider variables present in the current environment. It exits with `0` when at least one registry variable is present and `1` when none are present. Presence is not validation: the command does not verify a key, contact a provider, or inspect its permissions.

### `workhorse --version`

Prints the installed CLI version. `-V` is an alias.

### No arguments

Prints concise usage information and exits `0`.

## Output and automation

Interactive output uses restrained ANSI color. Color is automatically disabled when stdout is not a terminal. Set `NO_COLOR=1` to disable it explicitly:

```bash
NO_COLOR=1 workhorse providers > providers.txt
```

The Rust commands currently emit human-readable text rather than a versioned machine-readable format. Treat the output as presentation output; use the source registry or a future structured output mode for automation that requires a stable schema.

The Rust transport library is not a CLI command. No Rust command currently sends a model request, even when provider credentials are configured.

## Python compatibility commands

These commands are provided by the legacy Python package:

| Command | Purpose |
| --- | --- |
| `workhorse-legacy plan OBJECTIVE` | Generate a JSON execution plan without running it |
| `workhorse-legacy exec PLAN_FILE` | Execute a previously generated plan |
| `workhorse-legacy run OBJECTIVE` | Plan, execute, and deliver in one command |
| `workhorse-legacy status TASK_ID` | Read task state from the ledger |
| `workhorse-legacy ledger-tail` | Print the most recent ledger entries |

Use `workhorse-legacy --config PATH` or `WORKHORSE_CONFIG` to select Python configuration. Only `plan` and `run` require `GROQ_API_KEY`; ledger and status commands are local-only.
