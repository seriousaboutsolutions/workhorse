"""Test ledger append-only behavior."""
import tempfile
from pathlib import Path
from workhorse.ledger import Ledger
from workhorse.config import LedgerConfig


def test_append_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)

        h = ledger.append("test", task_id="t1", content={"msg": "hello"})
        assert len(h) == 16

        entries = ledger.get_entries(task_id="t1")
        assert len(entries) == 1
        assert entries[0]["type"] == "test"


def test_get_by_hash():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)
        h = ledger.append("test", task_id="t1", content={"msg": "hello"})
        entry = ledger.get_by_hash(h)
        assert entry is not None
        assert entry["task_id"] == "t1"


def test_compact():
    with tempfile.TemporaryDirectory() as tmp:
        config = LedgerConfig(path=f"{tmp}/ledger.jsonl", archive_path=f"{tmp}/archive/")
        ledger = Ledger(config)
        for i in range(3):
            ledger.append("tool_call", task_id="t1", step_id=str(i))

        h = ledger.compact("t1")
        assert h is not None

        state = ledger.get_task_state("t1")
        assert state["has_compaction"] is True
        assert state["total_entries"] == 1  # Only the compaction entry remains
