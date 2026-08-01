# Providers

## Support model

Provider support is intentionally split into two stages:

1. **Registry support:** the Rust CLI can list the provider, show its endpoint metadata, and detect its configured environment variable.
2. **Runtime support:** a provider can be selected by an execution transport and used for model requests.

All providers in the table below have registry support. OpenAI-compatible providers now share a Rust transport contract, but the Rust CLI does not yet expose a model-request command. The legacy Python execution runtime currently supports Groq only.

| ID | Environment variable | Default endpoint | Request protocol |
| --- | --- | --- | --- |
| `anthropic` | `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1` | Anthropic Messages |
| `gemini` | `GEMINI_API_KEY` | `https://generativelanguage.googleapis.com/v1beta` | Gemini |
| `groq` | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` | OpenAI-compatible, Rust transport |
| `mistral` | `MISTRAL_API_KEY` | `https://api.mistral.ai/v1` | OpenAI-compatible, Rust transport |
| `ollama` | `OLLAMA_HOST` | `http://localhost:11434/v1` | OpenAI-compatible, Rust transport |
| `openai` | `OPENAI_API_KEY` | `https://api.openai.com/v1` | OpenAI-compatible, Rust transport |
| `openrouter` | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` | OpenAI-compatible, Rust transport |
| `xai` | `XAI_API_KEY` | `https://api.x.ai/v1` | OpenAI-compatible, Rust transport |

The source of truth is `PROVIDERS` in [`src/provider.rs`](../src/provider.rs). Keep this document, the README, and provider tests synchronized when the registry changes. Transport behavior is documented separately in [`transport.md`](transport.md).

## Credential handling

- Workhorse reads variable presence for `doctor`; it does not print values.
- Workhorse does not persist credentials.
- Prefer short-lived, least-privilege credentials in a managed secret store.
- Use `OLLAMA_HOST` for the local Ollama endpoint; it is a host setting rather than an API key.
- Verify outbound network policy and provider data-retention terms before enabling a remote backend.

## Adding a provider

1. Add a `Provider` entry in `src/provider.rs` with a stable lowercase ID, display name, environment variable, endpoint, and typed protocol metadata.
2. Add the same row to this document and the README registry table.
3. Add or extend a Rust test for the provider class and uniqueness of its ID.
4. Update the `api_key_variables` list in `kaptaind.toml` when the provider uses a new credential variable.
5. If runtime support is added, implement or reuse a transport adapter and add request, response, error, and timeout fixtures.
6. Run `cargo test --offline`, `python3 -m pytest tests/ -q`, and review the documentation diff.

Registry support alone must not be documented as live runtime support.
