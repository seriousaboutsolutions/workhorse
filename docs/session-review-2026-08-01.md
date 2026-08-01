# Workhorse session review

**Date:** 2026-08-01  
**Repository:** `seriousaboutsolutions/workhorse`  
**Branch:** `main`  
**Closeout status:** shipped to `origin/main`

## Executive summary

This session moved Workhorse from a Groq-oriented Python prototype toward a documented Rust migration with an explicit provider boundary. The repository now has a usable Rust discovery CLI, typed provider metadata, a first provider transport adapter, safer compatibility execution, enterprise-oriented documentation, a branded terminal experience, and Kaptaind-managed release commits.

The central limitation remains deliberate and documented: the Rust binary does not expose model-request or task-execution commands yet. The OpenAI-compatible transport is a tested library boundary, not an end-user runtime feature.

## Delivered capabilities

### Product and runtime

- Rust CLI with `providers`, `doctor`, and version commands.
- Terminal styling with TTY detection and `NO_COLOR` support.
- Typed provider catalog covering Anthropic, Gemini, Groq, Mistral, Ollama, OpenAI, OpenRouter, and xAI.
- Protocol classification for Anthropic, Gemini, and OpenAI-compatible providers.
- OpenAI-compatible Rust transport using Reqwest, Rustls, Serde, and JSON normalization.
- Provider error taxonomy for authentication, rate limits, timeouts, transport failures, protocol failures, and unsupported adapters.
- 10-second connection timeout and 120-second request timeout at the transport boundary.
- Ollama endpoint resolution through `OLLAMA_HOST`.

### Compatibility runtime hardening

- Allowlisted process execution with `shell=False` by default.
- Shell operators and command chaining rejected by default.
- Explicit unsafe shell mode behind `allow_shell_operators`.
- Workspace-root enforcement for file tools and process working directories.
- Symlink-aware path resolution and policy error codes.
- Bounded executor parallelism, configured timeouts, retries, and fail-fast behavior.
- Retry-before-dependency-failure semantics.
- Thread-safe ledger append operations.
- Local status and ledger commands no longer require Groq credentials.
- Python executable renamed to `workhorse-legacy` to avoid collision with the Rust `workhorse` binary.

### Documentation and project operations

- Enterprise-oriented README and documentation index.
- CLI, getting-started, provider, transport, architecture, operations, contributing, and roadmap guides.
- VHS-authored terminal demo GIF and reproducible tape.
- Brand logo integrated into README and CLI presentation.
- Kaptaind monitoring, test hooks, versioning, and release workflow.
- Version source consolidated through `Cargo.toml`; Python packaging reads the same version.

## Evidence at closeout

| Check | Result |
| --- | --- |
| Rust unit tests | 4 passed |
| Python tests | 21 passed |
| Offline Cargo build/test | Passed |
| Package version consistency | Cargo/Python derive from the same manifest version |
| Documentation link/reference audit | Passed |
| Git whitespace check | Passed |
| Previous remote state | `origin/main` aligned at `47d1263` before this closeout |

The session's previous shipped commit is `47d1263 build(deps): update dependencies (Cargo.lock, Cargo.toml, +12 more)`. Kaptaind assigns the closeout release version and commit after the final documentation checks.

## Near-future targets

### 1. Expose a controlled Rust completion command

Add an application service above `ProviderTransport` with:

- explicit provider and model selection;
- config-file and environment resolution;
- `--json` output with a versioned schema;
- redacted errors and request correlation IDs;
- application-level retry classification and bounded backoff;
- a clear exit-code contract;
- no implicit network calls from `doctor`.

Completion must be opt-in and must not silently turn provider discovery into a network operation.

### 2. Complete the OpenAI-compatible contract suite

Add offline fixtures for:

- request method, endpoint, headers, and body shape;
- bearer authentication without secret capture;
- 401/403 authentication failures;
- 429 with valid, missing, and malformed `Retry-After`;
- connection timeout and response timeout;
- malformed JSON and missing response fields;
- provider response usage omissions and model fallback;
- Ollama no-key behavior.

### 3. Add provider-specific adapters

Implement Anthropic Messages and Gemini adapters behind the same normalized contract. Each adapter requires capability declarations, fixture coverage, typed error mapping, and opt-in live smoke tests. Registry entries must not be promoted to runtime support until all gates pass.

### 4. Finish Phase 0 execution isolation

The current workspace and allowlist controls are policy boundaries, not OS isolation. Next controls are:

- read/write mount policy;
- explicit artifact directories;
- process-tree cancellation;
- output-size limits;
- network egress policy and SSRF protection;
- container or restricted-worker execution;
- fork, memory, CPU, and file-size limits.

### 5. Move the application service into Rust

Port plan validation, DAG scheduling, ledger events, delivery, and compatibility fixtures into typed Rust modules. Keep Python as a compatibility adapter until golden-output and migration tests demonstrate parity.

### 6. Raise release and observability maturity

Add formatting, Clippy, dependency audit, license, SBOM, provenance, schema compatibility, benchmark, and redaction gates. Add OpenTelemetry-compatible traces and metrics only after content redaction and retention policies are defined.

## Current quality assessment

Workhorse is now a strong migration foundation, not a finished enterprise runtime. Its strongest areas are documentation honesty, provider boundary design, compatibility safety improvements, deterministic local diagnostics, and reproducible tests. Its largest remaining risks are incomplete Rust application integration, lack of full OS-level sandboxing, limited transport fixture coverage, and the absence of structured Rust CLI output.

## Closeout rules

- Treat the Rust CLI as discovery-only until a completion command is explicitly shipped and documented.
- Treat “Registry + transport” as library capability, not provider runtime availability.
- Keep live provider tests opt-in and secret-safe.
- Keep generated `.kaptaind/`, build output, credentials, and local environments out of Git.
- Update this review only for historical corrections; track active work in [`roadmap.md`](roadmap.md).
