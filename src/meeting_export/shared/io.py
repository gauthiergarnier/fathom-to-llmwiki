from __future__ import annotations

import re
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
    )
    try:
        tmp.write(content)
        tmp.close()
        Path(tmp.name).rename(path)
    except BaseException:
        Path(tmp.name).unlink(missing_ok=True)
        raise


def resolve_collision(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()
