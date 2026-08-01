"""CLI contract tests for local and credentialed commands."""
from click.testing import CliRunner

from workhorse.cli import main


def test_local_status_does_not_require_groq_key(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(
        "ledger:\n"
        f"  path: '{tmp_path / 'ledger.jsonl'}'\n"
        f"  archive_path: '{tmp_path / 'archive'}'\n"
    )
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    result = CliRunner().invoke(main, ["--config", str(config), "status", "missing"])

    assert result.exit_code == 0
    assert '"task_id": "missing"' in result.output


def test_model_commands_require_groq_key(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("ledger:\n  path: '%s'\n" % (tmp_path / "ledger.jsonl"))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    result = CliRunner().invoke(main, ["--config", str(config), "plan", "test objective"])

    assert result.exit_code != 0
    assert "GROQ_API_KEY not set" in result.output
