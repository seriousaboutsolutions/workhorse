# Workhorse documentation

This directory contains the maintained product documentation. Start with the guide that matches your task:

| Need | Document |
| --- | --- |
| Install the CLI or run the Python compatibility path | [`getting-started.md`](getting-started.md) |
| Find commands, exits, and output contracts | [`cli.md`](cli.md) |
| Understand provider coverage and add a provider | [`providers.md`](providers.md) |
| Understand the Rust/Python boundary | [`architecture.md`](architecture.md) |
| Operate Workhorse in local and CI environments | [`operations.md`](operations.md) |
| Contribute, test, record demos, or release | [`contributing.md`](contributing.md) |

The terminal demo is reproducible from [`demo.tape`](demo.tape). Its rendered artifact is [`demo.gif`](demo.gif). The tape uses a placeholder credential only to demonstrate local detection; it never contacts a provider.

## Documentation principles

- Describe shipped behavior before planned behavior.
- Make security boundaries and network behavior explicit.
- Prefer copy-pasteable commands with their expected exit semantics.
- Keep provider support claims tied to the implementation registry.
