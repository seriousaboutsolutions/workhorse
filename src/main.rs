//! Workhorse's Rust CLI.  The provider registry is deliberately local and
//! deterministic so `providers` is useful without network access or secrets.

use std::{env, fmt, io::{self, IsTerminal}, process::ExitCode};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Provider {
    id: &'static str,
    name: &'static str,
    env_key: &'static str,
    base_url: &'static str,
    protocol: &'static str,
}

const PROVIDERS: &[Provider] = &[
    Provider { id: "anthropic", name: "Anthropic", env_key: "ANTHROPIC_API_KEY", base_url: "https://api.anthropic.com/v1", protocol: "anthropic" },
    Provider { id: "gemini", name: "Google Gemini", env_key: "GEMINI_API_KEY", base_url: "https://generativelanguage.googleapis.com/v1beta", protocol: "gemini" },
    Provider { id: "groq", name: "Groq", env_key: "GROQ_API_KEY", base_url: "https://api.groq.com/openai/v1", protocol: "openai-compatible" },
    Provider { id: "mistral", name: "Mistral", env_key: "MISTRAL_API_KEY", base_url: "https://api.mistral.ai/v1", protocol: "openai-compatible" },
    Provider { id: "ollama", name: "Ollama", env_key: "OLLAMA_HOST", base_url: "http://localhost:11434/v1", protocol: "openai-compatible" },
    Provider { id: "openai", name: "OpenAI", env_key: "OPENAI_API_KEY", base_url: "https://api.openai.com/v1", protocol: "openai-compatible" },
    Provider { id: "openrouter", name: "OpenRouter", env_key: "OPENROUTER_API_KEY", base_url: "https://openrouter.ai/api/v1", protocol: "openai-compatible" },
    Provider { id: "xai", name: "xAI", env_key: "XAI_API_KEY", base_url: "https://api.x.ai/v1", protocol: "openai-compatible" },
];

impl fmt::Display for Provider {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:<12} {:<18} {:<24} {}", self.id, self.name, self.env_key, self.base_url)
    }
}

fn color_enabled() -> bool {
    io::stdout().is_terminal() && env::var_os("NO_COLOR").is_none()
}

fn paint(value: impl AsRef<str>, code: &str, enabled: bool) -> String {
    if enabled {
        format!("\x1b[{code}m{}\x1b[0m", value.as_ref())
    } else {
        value.as_ref().to_owned()
    }
}

fn usage() {
    let color = color_enabled();
    println!("{}", paint("workhorse", "1;36", color));
    println!("provider-neutral task execution");
    println!("\n{}", paint("USAGE", "1;37", color));
    println!("    {}  list supported providers", paint("workhorse providers", "36", color));
    println!("    {}     inspect configured credentials", paint("workhorse doctor", "36", color));
    println!("    {}  print the installed version", paint("workhorse --version", "36", color));
}

fn providers() {
    let color = color_enabled();
    println!("{}", paint("Supported providers", "1;36", color));
    println!("{}", paint("────────────────────────────────────────────────────────────────────────────────────────", "90", color));
    println!("{}", paint(format!("{:<12} {:<18} {:<24} {}", "ID", "PROVIDER", "API KEY / HOST", "BASE URL"), "1;37", color));
    println!("{}", paint("────────────────────────────────────────────────────────────────────────────────────────", "90", color));
    for provider in PROVIDERS {
        let row = format!("{provider}");
        println!("{}", paint(row, "37", color));
    }
    println!("\n{} providers registered", paint(PROVIDERS.len().to_string(), "1;32", color));
}

fn doctor() -> ExitCode {
    let color = color_enabled();
    let configured: Vec<_> = PROVIDERS.iter().filter(|p| env::var(p.env_key).is_ok()).collect();
    if configured.is_empty() {
        eprintln!("{}", paint("No provider credentials found.", "1;31", color));
        eprintln!("Set one of the API key variables listed by `workhorse providers`.");
        return ExitCode::from(1);
    }
    println!("{}", paint("Configured providers", "1;36", color));
    for provider in configured {
        println!("  {} {}", paint("●", "1;32", color), paint(format!("{} ({})", provider.id, provider.protocol), "32", color));
    }
    println!("\n{}", paint("Credentials detected; no network requests made.", "90", color));
    ExitCode::SUCCESS
}

fn main() -> ExitCode {
    match env::args().nth(1).as_deref() {
        Some("providers") => { providers(); ExitCode::SUCCESS }
        Some("doctor") => doctor(),
        Some("--version") | Some("-V") => { println!("workhorse {}", paint("0.2.0", "1;36", color_enabled())); ExitCode::SUCCESS }
        _ => { usage(); ExitCode::SUCCESS }
    }
}

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
    fn includes_openai_compatible_and_native_protocols() {
        assert!(PROVIDERS.iter().any(|p| p.protocol == "openai-compatible"));
        assert!(PROVIDERS.iter().any(|p| p.protocol == "anthropic"));
        assert!(PROVIDERS.iter().any(|p| p.protocol == "gemini"));
    }
}
