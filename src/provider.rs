//! Typed provider catalog. Runtime transports consume this contract without
//! coupling the CLI to provider-specific request logic.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Protocol {
    Anthropic,
    Gemini,
    OpenAiCompatible,
}

impl Protocol {
    pub const fn label(self) -> &'static str {
        match self {
            Self::Anthropic => "anthropic",
            Self::Gemini => "gemini",
            Self::OpenAiCompatible => "openai-compatible",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Provider {
    pub id: &'static str,
    pub name: &'static str,
    pub env_key: &'static str,
    pub base_url: &'static str,
    pub protocol: Protocol,
}

pub const PROVIDERS: &[Provider] = &[
    Provider { id: "anthropic", name: "Anthropic", env_key: "ANTHROPIC_API_KEY", base_url: "https://api.anthropic.com/v1", protocol: Protocol::Anthropic },
    Provider { id: "gemini", name: "Google Gemini", env_key: "GEMINI_API_KEY", base_url: "https://generativelanguage.googleapis.com/v1beta", protocol: Protocol::Gemini },
    Provider { id: "groq", name: "Groq", env_key: "GROQ_API_KEY", base_url: "https://api.groq.com/openai/v1", protocol: Protocol::OpenAiCompatible },
    Provider { id: "mistral", name: "Mistral", env_key: "MISTRAL_API_KEY", base_url: "https://api.mistral.ai/v1", protocol: Protocol::OpenAiCompatible },
    Provider { id: "ollama", name: "Ollama", env_key: "OLLAMA_HOST", base_url: "http://localhost:11434/v1", protocol: Protocol::OpenAiCompatible },
    Provider { id: "openai", name: "OpenAI", env_key: "OPENAI_API_KEY", base_url: "https://api.openai.com/v1", protocol: Protocol::OpenAiCompatible },
    Provider { id: "openrouter", name: "OpenRouter", env_key: "OPENROUTER_API_KEY", base_url: "https://openrouter.ai/api/v1", protocol: Protocol::OpenAiCompatible },
    Provider { id: "xai", name: "xAI", env_key: "XAI_API_KEY", base_url: "https://api.x.ai/v1", protocol: Protocol::OpenAiCompatible },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn provider_ids_are_unique() {
        for (index, provider) in PROVIDERS.iter().enumerate() {
            assert!(!PROVIDERS[index + 1..].iter().any(|other| other.id == provider.id));
        }
    }

    #[test]
    fn protocol_labels_are_stable() {
        assert_eq!(Protocol::Anthropic.label(), "anthropic");
        assert_eq!(Protocol::Gemini.label(), "gemini");
        assert_eq!(Protocol::OpenAiCompatible.label(), "openai-compatible");
    }
}
