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

`src/provider.rs` owns typed provider metadata and protocol classification. `src/transport.rs` defines the provider-neutral completion contract and the first OpenAI-compatible adapter. `src/main.rs` owns local CLI presentation; the current CLI remains discovery-only and does not invoke the transport. Transport errors are typed so authentication, rate limits, timeouts, network failures, and malformed responses can receive distinct retry and telemetry treatment.

The remaining migration boundary is provider-specific authentication and CLI/application integration. A complete runtime provider should define authentication, endpoint construction, request serialization, response normalization, timeout behavior, and error classification before it is promoted from registry support to runtime support.

The compatibility executor is intentionally policy-controlled: process steps use an allowlist and `shell=False`; shell operators are disabled by default. This is a baseline control, not a substitute for a container, sandbox, or OS-level isolation boundary.

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
