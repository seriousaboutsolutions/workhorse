# Architecture

## Current system

```text
                    +-------------------------+
                    | Rust CLI                 |
                    | providers / doctor      |
                    | local, deterministic    |
                    +------------+------------+
                                 |
                         provider registry
                                 |
 +-------------------+   +-------v---------+   +------------------+
 | Python CLI         |-->| Groq client     |-->| Groq API          |
 | plan / exec / run  |   | planning + chat |   | remote requests   |
 +---------+---------+   +-------+---------+   +------------------+
           |                       |
           v                       v
     task planner            append-only ledger
     and executor            ~/.workhorse/ledger.jsonl
```

The Rust and Python paths are separate entry points today. The Rust binary does not invoke the Python package, and the Python package does not consume the Rust provider registry.

## Rust boundary

`src/main.rs` owns the provider metadata and the local CLI presentation. It deliberately has no dependencies and makes no network calls. This keeps discovery usable in restricted build, CI, and incident environments.

The planned migration boundary is a provider transport abstraction beneath the registry. A complete runtime provider should define authentication, endpoint construction, request serialization, response normalization, timeout behavior, and error classification before it is promoted from registry support to runtime support.

## Python compatibility boundary

The Python package is organized around:

- `planner.py`: turns an objective into a structured `TaskPlan` through `GroqClient`.
- `executor.py`: executes plan steps and records tool calls.
- `ledger.py`: writes append-only JSON Lines entries and supports compaction.
- `deliverer.py`: formats execution results.
- `config.py`: loads YAML configuration and environment defaults.

This path remains the compatibility surface for existing users and tests during the Rust migration.

## Design constraints

- Keep provider discovery local and deterministic.
- Never print or persist secret values.
- Preserve plain output for pipes and CI.
- Keep ledger writes append-only during normal execution.
- Make the Rust transport boundary explicit before adding provider-specific behavior.
