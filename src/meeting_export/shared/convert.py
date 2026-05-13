from __future__ import annotations

from datetime import datetime

from .io import sanitize_filename


def yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def compute_duration(start: str, end: str) -> str:
    s, e = parse_dt(start), parse_dt(end)
    if not s or not e:
        return ""
    delta = e - s
    total_secs = int(delta.total_seconds())
    if total_secs < 0:
        return ""
    h, rem = divmod(total_secs, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}min"
    return f"{m} min"


def format_participants(invitees: list[dict]) -> list[str]:
    result = []
    for inv in invitees:
        name = inv.get("name", "")
        email = inv.get("email", "")
        if name and email:
            result.append(f"{name} <{email}>")
        elif email:
            result.append(email)
        elif name:
            result.append(name)
    return result


def make_filename(title: str, date_str: str) -> str:
    safe_title = sanitize_filename(title or "Untitled Meeting")
    if len(safe_title) > 100:
        safe_title = safe_title[:100].rstrip()
    date_prefix = date_str or "undated"
    return f"{date_prefix} - {safe_title}.md"
