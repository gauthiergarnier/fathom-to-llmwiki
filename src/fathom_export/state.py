from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_VERSION = 1


class SyncState:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict = {"version": _VERSION, "last_sync_at": None, "exported": {}}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Corrupt state file, starting fresh: %s", e)
            self._data = {"version": _VERSION, "last_sync_at": None, "exported": {}}

    def save(self) -> None:
        self._data["last_sync_at"] = datetime.now(timezone.utc).isoformat()
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def is_exported(self, recording_id: str | int) -> bool:
        return str(recording_id) in self._data.get("exported", {})

    def mark_exported(self, recording_id: str | int, title: str, file_path: str) -> None:
        self._data.setdefault("exported", {})[str(recording_id)] = {
            "title": title,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
        }

    @property
    def last_sync_at(self) -> datetime | None:
        ts = self._data.get("last_sync_at")
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None

    @property
    def exported_count(self) -> int:
        return len(self._data.get("exported", {}))

    def reset(self) -> None:
        self._data = {"version": _VERSION, "last_sync_at": None, "exported": {}}
        if self._path.exists():
            self._path.unlink()
