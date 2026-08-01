"""Append-only context ledger with hash-based references."""
import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import LedgerConfig

logger = logging.getLogger(__name__)


class Ledger:
    """Append-only execution log. Never re-summarize."""

    def __init__(self, config: Optional[LedgerConfig] = None):
        self.config = config or LedgerConfig()
        self.path = Path(self.config.path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.archive_path = Path(self.config.archive_path).expanduser()
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self._buffer: List[Dict] = []
        self._lock = threading.Lock()

    def append(
        self,
        entry_type: str,
        task_id: Optional[str] = None,
        content: Optional[Dict] = None,
        **kwargs,
    ) -> str:
        """Append an entry to the ledger. Returns the hash."""
        entry = {
            "type": entry_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
        }
        if content:
            entry["content"] = content
        entry.update(kwargs)

        entry_hash = self._hash(entry)
        entry["hash"] = entry_hash

        with self._lock:
            self._buffer.append(entry)
            self._flush()
        return entry_hash

    def _hash(self, data: Dict) -> str:
        """Compute a stable hash for an entry."""
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def _flush(self) -> None:
        """Write buffered entries to disk."""
        if not self._buffer:
            return
        with open(self.path, "a") as f:
            for entry in self._buffer:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._buffer.clear()

    def get_entries(self, task_id: Optional[str] = None, entry_type: Optional[str] = None) -> List[Dict]:
        """Retrieve entries by filter. References by hash, not content."""
        entries = []
        if not self.path.exists():
            return entries
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if task_id and entry.get("task_id") != task_id:
                    continue
                if entry_type and entry.get("type") != entry_type:
                    continue
                entries.append(entry)
        return entries

    def get_by_hash(self, entry_hash: str) -> Optional[Dict]:
        """Retrieve a single entry by hash."""
        for entry in self.get_entries():
            if entry.get("hash") == entry_hash:
                return entry
        return None

    def compact(self, task_id: str) -> str:
        """Compact a task's entries once. Never re-compact."""
        entries = self.get_entries(task_id=task_id)
        if not entries:
            return ""

        # Archive the original entries
        archive_file = self.archive_path / f"{task_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(archive_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Create a compacted summary entry
        summary = {
            "type": "compaction",
            "task_id": task_id,
            "original_count": len(entries),
            "original_hashes": [e["hash"] for e in entries],
            "archive_file": str(archive_file),
        }
        summary_hash = self.append("compaction", task_id=task_id, content=summary)

        # Remove original entries from the active ledger (rewrite file without them)
        self._rewrite_without(task_id, entries)
        logger.info(f"Compacted task {task_id}: {len(entries)} entries archived, summary hash {summary_hash}")
        return summary_hash

    def _rewrite_without(self, task_id: str, remove_entries: List[Dict]) -> None:
        """Rewrite ledger file excluding entries for a task."""
        remove_hashes = {e["hash"] for e in remove_entries}
        if not self.path.exists():
            return
        lines = []
        with open(self.path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("hash") not in remove_hashes:
                        lines.append(line)
                except json.JSONDecodeError:
                    lines.append(line)
        with open(self.path, "w") as f:
            f.writelines(lines)

    def get_task_state(self, task_id: str) -> Dict[str, Any]:
        """Get current state of a task from the ledger."""
        entries = self.get_entries(task_id=task_id)
        state = {
            "task_id": task_id,
            "total_entries": len(entries),
            "has_compaction": any(e["type"] == "compaction" for e in entries),
            "latest_entry": entries[-1] if entries else None,
        }
        return state
