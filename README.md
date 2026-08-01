<p align="center">
  <img src="assets/workhorse-logo.svg" alt="Workhorse" width="420">
</p>

<p align="center">Provider-neutral task execution for dependable automation.</p>

Workhorse is a provider-neutral task execution CLI. The Rust CLI keeps provider discovery and local diagnostics fast and predictable; the original Python package remains available while the execution engine is being migrated.

![Workhorse provider discovery](docs/demo.gif)

## Install and run

Rust 1.70 or newer is required for the CLI:

```bash
cargo install --path .
workhorse providers
workhorse doctor
```

`providers` prints every supported backend and its credential variable. `doctor` reports which backends are configured without making a network request.

## Supported providers

| Provider | Environment variable | API style |
| --- | --- | --- |
| Anthropic | `ANTHROPIC_API_KEY` | Anthropic Messages |
| Google Gemini | `GEMINI_API_KEY` | Gemini |
| Groq | `GROQ_API_KEY` | OpenAI-compatible |
| Mistral | `MISTRAL_API_KEY` | OpenAI-compatible |
| Ollama | `OLLAMA_HOST` | OpenAI-compatible, local |
| OpenAI | `OPENAI_API_KEY` | OpenAI-compatible |
| OpenRouter | `OPENROUTER_API_KEY` | OpenAI-compatible |
| xAI | `XAI_API_KEY` | OpenAI-compatible |

Set one credential before running `doctor`, for example:

```bash
export OPENAI_API_KEY=...
workhorse doctor
```

No credential is stored by Workhorse. Provider endpoints and protocol metadata live in the local registry in `src/main.rs`.

## Development

```bash
cargo test
python3 -m pytest tests/ -v
vhs docs/demo.tape
```

The VHS tape regenerates the animated terminal demo at `docs/demo.gif`. Install [VHS](https://github.com/charmbracelet/vhs) if you want to regenerate it locally.

## Python compatibility

The existing Python task planner and executor can still be installed for compatibility:

```bash
pip install -e .
workhorse run "your task here"
```

The Python path currently uses Groq; new provider integrations should target the Rust provider registry and protocol boundary.
