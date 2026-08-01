//! Workhorse's Rust CLI.  The provider registry is deliberately local and
//! deterministic so `providers` is useful without network access or secrets.

use std::{env, io::{self, IsTerminal}, process::ExitCode};
pub mod provider;
pub mod transport;

use provider::PROVIDERS;

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
    println!("{}", paint("WORKHORSE", "1;36", color));
    println!("{}", paint("provider-neutral task execution", "90", color));
    println!("\n{}", paint("USAGE", "1;37", color));
    println!("    {}  list supported providers", paint("workhorse providers", "36", color));
    println!("    {}     inspect configured credentials", paint("workhorse doctor", "36", color));
    println!("    {}  print the installed version", paint("workhorse --version", "36", color));
}

fn providers() {
    let color = color_enabled();
    println!("{}", paint("Supported providers", "1;36", color));
    println!("{}", paint("Local registry · no network requests", "90", color));
    println!("{}", paint("────────────────────────────────────────────────────────────────────────────────────────────────────────────", "90", color));
    println!("{}", paint(format!("{:<12} {:<18} {:<24} {:<19} {}", "ID", "PROVIDER", "API KEY / HOST", "PROTOCOL", "BASE URL"), "1;37", color));
    println!("{}", paint("────────────────────────────────────────────────────────────────────────────────────────────────────────────", "90", color));
    for provider in PROVIDERS {
        let protocol = if provider.protocol.label() == "openai-compatible" { "OpenAI-compatible" } else { provider.protocol.label() };
        println!(
            "{} {} {} {} {}",
            paint(format!("{:<12}", provider.id), "1;36", color),
            paint(format!("{:<18}", provider.name), "37", color),
            paint(format!("{:<24}", provider.env_key), "33", color),
            paint(format!("{:<19}", protocol), "35", color),
            paint(provider.base_url, "90", color),
        );
    }
    println!("\n{}", paint(format!("{} providers registered · registry ready", PROVIDERS.len()), "1;32", color));
}

fn doctor() -> ExitCode {
    let color = color_enabled();
    let configured: Vec<_> = PROVIDERS.iter().filter(|p| env::var(p.env_key).is_ok()).collect();
    if configured.is_empty() {
        eprintln!("{}", paint("LOCAL DIAGNOSTICS · attention required", "1;31", color));
        eprintln!("{}", paint("No provider credentials found.", "31", color));
        eprintln!("Set one of the API key variables listed by `workhorse providers`.");
        return ExitCode::from(1);
    }
    println!("{}", paint("LOCAL DIAGNOSTICS · ready", "1;36", color));
    println!("{}", paint(format!("{}/{} provider variables detected", configured.len(), PROVIDERS.len()), "90", color));
    for provider in configured {
        println!("  {} {}", paint("●", "1;32", color), paint(format!("{} ({})", provider.id, provider.protocol.label()), "32", color));
    }
    println!("\n{}", paint("Credentials detected; no network requests made.", "90", color));
    ExitCode::SUCCESS
}

fn main() -> ExitCode {
    match env::args().nth(1).as_deref() {
        Some("providers") => { providers(); ExitCode::SUCCESS }
        Some("doctor") => doctor(),
        Some("--version") | Some("-V") => { println!("workhorse {}", paint(env!("CARGO_PKG_VERSION"), "1;36", color_enabled())); ExitCode::SUCCESS }
        _ => { usage(); ExitCode::SUCCESS }
    }
}
