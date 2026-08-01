# Contributing

## Local quality gate

Run the same checks used by Kaptaind:

```bash
cargo test
python3 -m pytest tests/ -v
git diff --check
```

For documentation or terminal-demo changes, also run:

```bash
vhs docs/demo.tape
```

VHS is optional for code-only changes. The generated `docs/demo.gif` should be regenerated when the demo commands or their visible output change.

## Change guidelines

- Keep the Rust binary dependency-free unless a dependency removes meaningful risk or complexity.
- Add tests for new provider metadata and command behavior.
- Keep output stable under `NO_COLOR=1`.
- Document current behavior and label migration work as planned.
- Never commit secrets, generated `.kaptaind/` state, `target/`, or local virtual environments.
- Update README and the focused document together when a user-facing contract changes.

## Release workflow

Kaptaind owns repository release analysis and may update the Cargo version. Before pushing a release commit:

1. Review the generated version and staged file list.
2. Run both test suites.
3. Confirm `git status` is clean after the commit.
4. Push the intended branch and verify the remote commit.

The canonical branch and remote are defined in [`kaptaind.toml`](../kaptaind.toml).
