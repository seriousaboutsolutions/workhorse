//! Provider-neutral transport contract.
//!
//! This module defines the runtime seam without claiming that network
//! the first OpenAI-compatible adapter. Concrete adapters can be added
//! without changing scheduler or CLI contracts.

use crate::provider::Provider;
use reqwest::blocking::Client;
use serde::Serialize;
use std::time::Duration;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompletionRequest {
    pub model: String,
    pub prompt: String,
    pub max_tokens: Option<u32>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompletionResponse {
    pub provider_id: String,
    pub model: String,
    pub content: String,
    pub input_tokens: u32,
    pub output_tokens: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProviderError {
    UnsupportedTransport { provider_id: String },
    Authentication { provider_id: String },
    RateLimited { retry_after_seconds: Option<u64> },
    Timeout,
    Transport { message: String },
    Protocol { message: String },
}

pub trait ProviderTransport: Send + Sync {
    fn provider(&self) -> Provider;
    fn complete(&self, request: &CompletionRequest) -> Result<CompletionResponse, ProviderError>;
}

fn normalize_response(provider: Provider, request: &CompletionRequest, body: serde_json::Value) -> Result<CompletionResponse, ProviderError> {
    let content = body["choices"][0]["message"]["content"].as_str().ok_or_else(|| ProviderError::Protocol { message: "response did not contain choices[0].message.content".to_owned() })?;
    Ok(CompletionResponse {
        provider_id: provider.id.to_owned(),
        model: body["model"].as_str().unwrap_or(&request.model).to_owned(),
        content: content.to_owned(),
        input_tokens: body["usage"]["prompt_tokens"].as_u64().unwrap_or(0) as u32,
        output_tokens: body["usage"]["completion_tokens"].as_u64().unwrap_or(0) as u32,
    })
}

/// Explicit placeholder used by discovery-only builds.
pub struct RegistryOnlyTransport {
    provider: Provider,
}

impl RegistryOnlyTransport {
    pub const fn new(provider: Provider) -> Self {
        Self { provider }
    }
}

impl ProviderTransport for RegistryOnlyTransport {
    fn provider(&self) -> Provider {
        self.provider
    }

    fn complete(&self, _request: &CompletionRequest) -> Result<CompletionResponse, ProviderError> {
        Err(ProviderError::UnsupportedTransport { provider_id: self.provider.id.to_owned() })
    }
}

#[derive(Serialize)]
struct ChatMessage<'a> {
    role: &'static str,
    content: &'a str,
}

#[derive(Serialize)]
struct ChatRequest<'a> {
    model: &'a str,
    messages: Vec<ChatMessage<'a>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
}

/// Blocking OpenAI-compatible transport shared by compatible providers.
pub struct OpenAiCompatibleTransport {
    provider: Provider,
    api_key: Option<String>,
    client: Client,
    endpoint: String,
}

impl OpenAiCompatibleTransport {
    pub fn new(provider: Provider, endpoint: String, api_key: Option<String>) -> Result<Self, ProviderError> {
        if provider.protocol.label() != "openai-compatible" {
            return Err(ProviderError::UnsupportedTransport { provider_id: provider.id.to_owned() });
        }
        Ok(Self {
            provider,
            api_key,
            client: Client::builder()
                .connect_timeout(Duration::from_secs(10))
                .timeout(Duration::from_secs(120))
                .build()
                .map_err(|error| ProviderError::Transport { message: error.to_string() })?,
            endpoint,
        })
    }

    pub fn from_environment(provider: Provider) -> Result<Self, ProviderError> {
        if provider.protocol.label() != "openai-compatible" {
            return Err(ProviderError::UnsupportedTransport { provider_id: provider.id.to_owned() });
        }
        let api_key = std::env::var(provider.env_key).ok().filter(|value| !value.is_empty());
        let base = if provider.id == "ollama" {
            std::env::var("OLLAMA_HOST").unwrap_or_else(|_| provider.base_url.trim_end_matches("/v1").to_owned())
        } else {
            provider.base_url.to_owned()
        };
        Self::new(provider, format!("{}/chat/completions", base.trim_end_matches('/')), api_key)
    }
}

impl ProviderTransport for OpenAiCompatibleTransport {
    fn provider(&self) -> Provider {
        self.provider
    }

    fn complete(&self, request: &CompletionRequest) -> Result<CompletionResponse, ProviderError> {
        let payload = ChatRequest {
            model: &request.model,
            messages: vec![ChatMessage { role: "user", content: &request.prompt }],
            max_tokens: request.max_tokens,
        };
        let mut request_builder = self.client.post(&self.endpoint).json(&payload);
        if let Some(api_key) = &self.api_key {
            request_builder = request_builder.bearer_auth(api_key);
        }
        let response = request_builder.send().map_err(|error| {
            if error.is_timeout() { ProviderError::Timeout } else { ProviderError::Transport { message: error.to_string() } }
        })?;
        let status = response.status();
        if status == reqwest::StatusCode::UNAUTHORIZED || status == reqwest::StatusCode::FORBIDDEN {
            return Err(ProviderError::Authentication { provider_id: self.provider.id.to_owned() });
        }
        if status == reqwest::StatusCode::TOO_MANY_REQUESTS {
            let retry_after_seconds = response.headers().get("retry-after").and_then(|value| value.to_str().ok()).and_then(|value| value.parse().ok());
            return Err(ProviderError::RateLimited { retry_after_seconds });
        }
        if !status.is_success() {
            return Err(ProviderError::Protocol { message: format!("provider returned HTTP {}", status.as_u16()) });
        }
        let body: serde_json::Value = response.json().map_err(|error| ProviderError::Protocol { message: format!("invalid provider response: {error}") })?;
        normalize_response(self.provider, request, body)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::provider::PROVIDERS;

    #[test]
    fn discovery_transport_fails_closed() {
        let transport = RegistryOnlyTransport::new(PROVIDERS[0]);
        let result = transport.complete(&CompletionRequest {
            model: "test".to_owned(),
            prompt: "hello".to_owned(),
            max_tokens: None,
        });
        assert_eq!(result, Err(ProviderError::UnsupportedTransport { provider_id: "anthropic".to_owned() }));
    }

    #[test]
    fn normalizes_openai_compatible_response_without_external_network() {
        let request = CompletionRequest { model: "fixture-model".to_owned(), prompt: "hello".to_owned(), max_tokens: Some(10) };
        let response = normalize_response(PROVIDERS[2], &request, serde_json::json!({
            "model": "fixture-model",
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2}
        })).expect("completion");

        assert_eq!(response.provider_id, "groq");
        assert_eq!(response.content, "hello");
        assert_eq!(response.input_tokens, 3);
        assert_eq!(response.output_tokens, 2);
    }
}
