# Provider transport reference

## Status

The Rust crate now contains a typed `ProviderTransport` contract and a blocking OpenAI-compatible adapter in [`src/transport.rs`](../src/transport.rs). The `workhorse` binary does not expose a completion command yet; `providers` and `doctor` remain local-only.

| Capability | Current state |
| --- | --- |
| Provider registry | Shipped for eight providers |
| OpenAI-compatible request adapter | Shipped as a Rust library boundary |
| Anthropic adapter | Registry only |
| Gemini adapter | Registry only |
| CLI model request command | Not yet exposed |
| Streaming responses | Not yet implemented |
| Tool-call normalization | Not yet implemented |
| Application-level retries | Not yet wired to the Rust service |

Do not treat “Registry + transport” as end-user runtime availability. A provider becomes runtime-supported only when the adapter is reachable through the application service, has policy and timeout coverage, and passes the provider contract suite.

## Request model

The current transport accepts a normalized request:

```text
CompletionRequest {
  model: String,
  prompt: String,
  max_tokens: Option<u32>,
}
```

It emits a normalized response containing provider ID, model, content, input tokens, and output tokens. Provider-specific JSON remains inside the adapter.

## OpenAI-compatible adapter

The adapter posts to `/chat/completions` and sends:

```json
{
  "model": "model-id",
  "messages": [{"role": "user", "content": "prompt"}],
  "max_tokens": 256
}
```

`max_tokens` is omitted when unset. API-key providers use a bearer token. Ollama uses `OLLAMA_HOST` as an endpoint setting and does not require a bearer token.

The client enforces a 10-second connect timeout and a 120-second total request timeout. These are transport defaults, not yet application-configurable values.

## Error semantics

| Error | Meaning | Retry policy |
| --- | --- | --- |
| `Authentication` | HTTP 401 or 403 | Never retry automatically |
| `RateLimited` | HTTP 429, including parsed `Retry-After` | Retry only in the application layer with bounded backoff |
| `Timeout` | Connect or request timeout | Retry only when the request is idempotent |
| `Transport` | DNS, TLS, socket, or client construction failure | Classify before retrying |
| `Protocol` | Non-success HTTP or malformed response | Do not blindly retry |
| `UnsupportedTransport` | Provider protocol has no adapter | Configuration/development failure |

Error messages intentionally avoid API-key values and response bodies. Request and response content must not be added to logs or ledger entries without explicit redaction policy.

## Testing contract

Transport tests must be offline by default:

- fixture tests validate normalized success responses;
- fixture tests cover 401, 403, 429, timeout, malformed JSON, and missing fields;
- request fixtures verify method, endpoint, headers, and omission of unset fields;
- live provider tests are opt-in, budgeted, and never required for pull requests.

New adapters must implement the same normalized contract and document any provider-specific capability gaps.
