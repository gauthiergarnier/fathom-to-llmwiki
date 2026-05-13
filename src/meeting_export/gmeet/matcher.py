from __future__ import annotations

import logging
import re
from datetime import datetime

from googleapiclient.discovery import Resource

from ..shared.convert import parse_dt
from .drive_client import export_doc_text

log = logging.getLogger(__name__)

_DATE_HEADER_RE = re.compile(
    r"^([A-Z][a-z]+ \d{1,2}, \d{4})\s*\|",
)


class MatchResult:
    def __init__(self) -> None:
        self.matched: list[dict] = []
        self.no_transcript: list[dict] = []
        self.errors: list[tuple[dict, str]] = []


def match_events_to_transcripts(
    drive_service: Resource,
    events: list[dict],
) -> MatchResult:
    result = MatchResult()

    for event in events:
        title = event.get("title", "Untitled Meeting")
        notes_att = event.get("notes_attachment")

        if not notes_att:
            log.debug("No notes attachment for: %s", title)
            result.no_transcript.append(event)
            continue

        file_id = notes_att["file_id"]
        att_title = notes_att.get("title", "")
        is_gemini = "gemini" in att_title.lower()

        try:
            full_text = export_doc_text(drive_service, file_id)
        except Exception as e:
            log.warning("Error exporting notes for '%s': %s", title, e)
            result.errors.append((event, str(e)))
            continue

        if is_gemini:
            transcript_text = full_text
        else:
            event_date = parse_dt(event.get("start", ""))
            transcript_text = _extract_section_for_date(full_text, event_date)
            if not transcript_text:
                log.debug("Manual notes section empty for: %s", title)
                result.no_transcript.append(event)
                continue

        result.matched.append({
            "event": event,
            "transcript_doc": {"id": file_id, "name": att_title},
            "transcript_text": transcript_text,
            "notes_text": "",
            "is_gemini": is_gemini,
        })

    return result


def _extract_section_for_date(
    text: str,
    event_date: datetime | None,
) -> str:
    if not event_date:
        return ""

    target = event_date.strftime("%b %-d, %Y")
    lines = text.replace("\r\n", "\n").split("\n")

    section_start = None
    for i, line in enumerate(lines):
        m = _DATE_HEADER_RE.match(line.strip())
        if m and m.group(1) == target:
            section_start = i
            break

    if section_start is None:
        return ""

    section_end = len(lines)
    for i in range(section_start + 1, len(lines)):
        if _DATE_HEADER_RE.match(lines[i].strip()):
            section_end = i
            break

    section_lines = lines[section_start:section_end]
    content = "\n".join(section_lines).strip()

    content = re.sub(r"__{5,}", "", content).strip()

    has_content = False
    for line in section_lines:
        stripped = line.strip()
        if _DATE_HEADER_RE.match(stripped):
            continue
        if stripped.startswith("Attendees:"):
            continue
        if stripped in ("Notes", "Action items", ""):
            continue
        if stripped == "*":
            continue
        has_content = True
        break

    if not has_content:
        return ""

    return content
