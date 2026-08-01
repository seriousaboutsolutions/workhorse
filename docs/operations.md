# Operations

## Health and diagnostics

`workhorse doctor` is a local configuration check, not a provider health check. A successful result means only that at least one configured variable exists in the process environment.

```bash
workhorse doctor
echo $?
```

For a provider connectivity check, use that provider's approved CLI or API health mechanism. Do not add live requests to `doctor` without defining timeout, retry, redaction, and failure semantics first.

## CI

Use non-interactive output in CI:

```bash
export NO_COLOR=1
cargo test
python3 -m pytest tests/ -q
```

Do not expose API keys in command output. CI should inject secrets into the job environment and revoke them through the provider's normal control plane.

## Logging and data

The Rust CLI emits only command results. The Python runtime writes task metadata, statuses, hashes, and tool results to the ledger path configured in YAML. Review ledger retention and archive permissions before using it with sensitive objectives or file content.

The default Python paths are:

```text
~/.workhorse/ledger.jsonl
~/.workhorse/archive/
```

## Kaptaind

Kaptaind watches `src/`, `Cargo.toml`, `workhorse/`, `tests/`, and `docs/`. Its pre-commit checks are:

```text
cargo test
python3 -m pytest tests/ -v
```

Review generated version changes and the final diff before allowing a release commit. Runtime state under `.kaptaind/` is intentionally ignored by Git.
