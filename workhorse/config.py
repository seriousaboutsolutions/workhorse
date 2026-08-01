"""Configuration management for workhorse."""
import os
import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class GroqConfig(BaseModel):
    api_key: str = Field(default_factory=lambda: os.environ.get("GROQ_API_KEY", ""))
    model: str = "llama-3.3-70b-versatile"
    base_url: str = "https://api.groq.com"
    context_window: int = 128000
    planning_reserve: int = 5000
    delivery_reserve: int = 3000
    temperature: float = 0.0
    max_tokens: Optional[int] = None


class ExecutionConfig(BaseModel):
    max_parallel: int = 8
    timeout: float = 300.0
    retry_count: int = 1
    fail_fast: bool = True
    shell_allowlist: list[str] = Field(default_factory=lambda: [
        "cat", "date", "echo", "find", "git", "grep", "ls", "pwd", "pytest",
        "whoami",
    ])
    allow_shell_operators: bool = False
    workspace_root: Optional[str] = "."


class LedgerConfig(BaseModel):
    path: str = "~/.workhorse/ledger.jsonl"
    compaction_threshold: float = 0.90
    archive_path: str = "~/.workhorse/archive/"


class Config(BaseModel):
    groq: GroqConfig = Field(default_factory=GroqConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    ledger: LedgerConfig = Field(default_factory=LedgerConfig)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        if path is None:
            path = os.environ.get("WORKHORSE_CONFIG", "~/.workhorse/config.yaml")
        config_path = Path(path).expanduser()
        if config_path.exists():
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

    def execution_budget(self) -> int:
        return (
            self.groq.context_window
            - self.groq.planning_reserve
            - self.groq.delivery_reserve
        )
