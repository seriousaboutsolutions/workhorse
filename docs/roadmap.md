# Workhorse SOTA roadmap

This roadmap defines the engineering path from the current migration scaffold to a production-grade, provider-neutral execution platform. “SOTA” means secure-by-default execution, normalized multi-provider runtime behavior, reproducible operations, measurable reliability, and an API contract that can evolve without breaking automation.

The roadmap is deliberately gate-based. A phase is complete only when its exit criteria are met and the evidence is checked into CI or release artifacts. Feature availability alone is not completion.

## Baseline

The current repository contains two paths:

- Rust: dependency-free provider registry, `providers`, and local `doctor` diagnostics.
- Python: compatibility planner, Groq client, task executor, JSONL ledger, and deliverer.

The Rust path does not yet make model requests. The Python path remains useful, but its process policy is a baseline allowlist rather than a full OS sandbox. These constraints are inputs to the plan, not hidden assumptions.

## Target architecture

```text
                         +-------------------------------+
                         | workhorse CLI                  |
                         | human, JSON, JSONL, exit codes |
                         +---------------+---------------+
                                         |
                         +---------------v---------------+
                         | application service            |
                         | plan -> execute -> deliver     |
                         +-------+---------------+--------+
                                 |               |
                    +------------v----+   +------v-----------+
                    | provider catalog |   | execution engine |
                    | IDs, capabilities|   | DAG + policies   |
                    +------------+----+   +------+------------+
                                 |               |
                    +------------v----+   +------v-----------+
                    | transport layer  |   | tool runtime     |
                    | auth, HTTP, retry |   | sandbox adapter  |
                    +------------+----+   +------+------------+
                                 |               |
                  +--------------v--+       +----v-------------+
                  | provider APIs    |       | OS/container/WASM |
                  +-----------------+       +------------------+
```

The Rust crate should own the application service, catalog, transport contracts, execution engine, CLI, and structured output. Python becomes a compatibility adapter with a documented end-of-life policy, not a second implementation of core behavior.

## Non-negotiable design contracts

### Provider contract

Define a stable Rust interface before adding provider-specific code:

```rust
trait ProviderTransport: Send + Sync {
    fn capabilities(&self) -> ProviderCapabilities;
    async fn complete(&self, request: CompletionRequest) -> Result<CompletionResponse, ProviderError>;
}
```

The production interface must cover:

- authentication without exposing secrets in errors or telemetry;
- endpoint and model resolution;
- streaming and non-streaming completion;
- tool calls and structured output;
- provider-neutral usage accounting;
- timeout, cancellation, retry, and rate-limit semantics;
- typed errors distinguishing authentication, quota, transport, protocol, and policy failures.

Provider adapters must be contract-tested against recorded fixtures and, where permitted, a live smoke test. Registry presence alone must never imply runtime support.

### Execution contract

Plans are validated before execution:

- unique step IDs;
- all dependencies exist;
- the graph is acyclic;
- actions are known and authorized;
- paths and network destinations satisfy policy;
- token and wall-clock budgets are valid.

Execution must provide deterministic dependency semantics, bounded concurrency, cancellation propagation, idempotency keys, retry classification, and a complete terminal state for every step. A retry must finish before failure is propagated to dependents.

### Output contract

Every command must support:

- human-readable terminal output;
- stable `--json` output for automation;
- `NO_COLOR` and non-TTY behavior;
- documented exit codes;
- redaction of credentials, authorization headers, and configured sensitive fields.

Human output is presentation. JSON schemas are the compatibility contract and must be versioned when breaking changes are unavoidable.

## Phased delivery plan

### Phase 0: foundation hardening

**Objective:** make the current compatibility path safe and measurable.

Deliverables:

- retain `shell=False` allowlisted execution as the default;
- add an explicit workspace root and path traversal protection for file tools;
- move unsafe shell execution behind an opt-in policy with a startup warning;
- enforce execution timeout, retry, concurrency, and fail-fast configuration;
- add structured error codes and redaction utilities;
- add CLI integration tests and dependency-graph property tests.

Exit criteria:

- no unbounded subprocess or network operation in the default profile;
- malicious path, command, and argument corpus produces policy failures;
- race-enabled ledger tests pass repeatedly under parallel execution;
- security review signs off on the compatibility profile.

### Phase 1: Rust domain model

**Objective:** move contracts out of CLI code and make them testable without network access.

Deliverables:

- modules for `config`, `provider`, `transport`, `plan`, `execution`, `ledger`, and `output`;
- typed IDs, capabilities, requests, responses, errors, and policy decisions;
- serde-based config and JSON output with schema fixtures;
- dependency graph validator and deterministic scheduler;
- compatibility fixtures proving Python and Rust plan/result equivalence.

Exit criteria:

- core behavior is covered without invoking a subprocess or provider;
- public structs have documented invariants;
- `cargo test`, formatting, linting, audit, and deny checks are mandatory CI gates.

### Phase 2: provider transport runtime

**Objective:** make the registry executable through a single normalized transport boundary.

Recommended implementation order:

1. OpenAI-compatible transport for OpenAI, Groq, Mistral, OpenRouter, xAI, and Ollama.
2. Anthropic Messages transport.
3. Gemini transport.

Deliverables:

- connection pooling and bounded request concurrency;
- explicit per-provider model and endpoint configuration;
- exponential backoff with jitter for retryable failures;
- `Retry-After` and provider quota handling;
- streaming cancellation and response-size limits;
- fixture, contract, and opt-in live tests for each adapter.

Exit criteria:

- identical logical requests produce normalized responses across adapters;
- authentication failures never retry;
- rate-limit behavior is tested from fixtures;
- secrets are absent from logs, traces, ledger entries, and crash reports.

### Phase 3: sandboxed tool runtime

**Objective:** replace process policy with enforceable isolation.

Deliverables:

- a `ToolRuntime` trait with local, container, and restricted-worker implementations;
- read-only workspace mounts by default;
- explicit writable paths and ephemeral working directories;
- CPU, memory, process-count, file-size, network, and wall-clock limits;
- syscall or container profile appropriate to the deployment target;
- cancellation that kills the complete process tree;
- artifact capture with size and content-type limits.

Exit criteria:

- escape, symlink, fork-bomb, oversized output, and network-egress tests pass;
- the default runtime cannot write outside its workspace;
- production deployment documentation specifies the isolation backend and residual risks.

### Phase 4: durable state and reliability

**Objective:** make executions resumable, auditable, and safe to operate.

Deliverables:

- versioned event schema with hash chaining and monotonic sequence numbers;
- atomic append and crash recovery;
- idempotency keys for task and step execution;
- resumable runs with explicit state-machine transitions;
- retention, encryption-at-rest integration, archive verification, and redaction;
- migration tooling for the Python JSONL ledger.

Exit criteria:

- kill-and-resume tests do not duplicate non-idempotent work;
- corrupted or truncated records are detected and surfaced;
- recovery runbooks are tested from backup artifacts.

### Phase 5: production observability

**Objective:** provide actionable telemetry without leaking task data.

Deliverables:

- OpenTelemetry traces and metrics with opt-in content capture;
- metrics for latency, queue depth, retries, provider errors, tokens, cost, and sandbox violations;
- correlation IDs across CLI, planner, provider, executor, and ledger;
- redacted structured logs with configurable retention;
- health, readiness, and diagnostic commands with clear network behavior.

Initial service objectives:

| Signal | Target |
| --- | --- |
| Local command startup | p95 < 100 ms excluding process startup |
| Provider request success | >= 99.5% excluding provider outage and invalid credentials |
| Scheduler duplicate execution | 0 known duplicates for idempotent steps |
| Ledger write durability | acknowledged entries survive process crash |
| Secret leakage | 0 secrets in automated redaction corpus |
| Release rollback | documented and rehearsed in < 15 minutes |

### Phase 6: compatibility and migration

**Objective:** make Rust the sole supported runtime without surprising current users.

Deliverables:

- a Rust compatibility mode for Python plan/result formats;
- migration command for config and ledger data;
- deprecation warnings and a published Python support window;
- golden-output tests for representative existing workflows;
- package naming and installation guidance with no executable collision;
- staged rollout: opt-in, default-on, then Python maintenance-only.

Exit criteria:

- all documented Python workflows have a Rust equivalent or explicit exception;
- migration is reversible;
- one release cycle completes with no unexplained compatibility regressions.

### Phase 7: ecosystem and governance

**Objective:** make provider and tool integrations safe to extend at scale.

Deliverables:

- versioned provider SDK and contribution template;
- capability negotiation and feature flags;
- signed release artifacts, SBOM, provenance attestations, and dependency policy;
- security policy, threat model, incident response, and disclosure process;
- compatibility matrix and support lifecycle;
- benchmark suite covering throughput, tail latency, cost, and failure recovery.

Exit criteria:

- reproducible builds and verified artifacts are published;
- release gates include security, compatibility, performance, and documentation checks;
- third-party providers can be added without modifying scheduler semantics.

## Required test strategy

The target test pyramid is:

- **Unit:** parsers, validators, redactors, policy decisions, retry classification, and state transitions.
- **Property:** DAG validity, scheduler determinism, ledger recovery, argument escaping, and redaction.
- **Contract:** provider request/response fixtures and normalized error behavior.
- **Integration:** real subprocess, filesystem, cancellation, and local provider tests.
- **End-to-end:** isolated provider smoke tests, resumable runs, and CLI JSON contracts.
- **Performance:** concurrency, tail latency, memory, ledger throughput, and provider backpressure.
- **Security:** path traversal, command injection, secret leakage, sandbox escape, SSRF, and denial-of-service corpus.

No live provider test should be required for a normal pull request. Live tests must be separately gated, budgeted, redacted, and disposable.

## Release gates

Every release candidate must produce:

1. passing Rust and Python compatibility suites;
2. formatting, lint, dependency audit, and license checks;
3. SBOM and provenance metadata;
4. migration and rollback verification;
5. updated CLI schema, provider matrix, architecture notes, and VHS demo;
6. a signed artifact and checksum manifest;
7. an explicit list of known residual risks.

The roadmap is complete only when the product can make a narrow, testable claim for each supported provider, execution mode, and deployment profile.
