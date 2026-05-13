from __future__ import annotations

import logging
from datetime import datetime

from googleapiclient.discovery import Resource

from ..shared.convert import parse_dt
from .drive_client import export_doc_text, find_meeting_notes, find_transcript

log = logging.getLogger(__name__)


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
        event_date = parse_dt(event.get("start", ""))

        if not event_date:
            log.warning("Skipping event with no parseable date: %s", title)
            result.errors.append((event, "no parseable date"))
            continue

        try:
            transcript_doc = find_transcript(drive_service, title, event_date)
        except Exception as e:
            log.warning("Error searching transcript for '%s': %s", title, e)
            result.errors.append((event, str(e)))
            continue

        if not transcript_doc:
            log.debug("No transcript found for: %s", title)
            result.no_transcript.append(event)
            continue

        try:
            transcript_text = export_doc_text(drive_service, transcript_doc["id"])
        except Exception as e:
            log.warning("Error exporting transcript for '%s': %s", title, e)
            result.errors.append((event, str(e)))
            continue

        notes_text = ""
        try:
            notes_doc = find_meeting_notes(drive_service, title, event_date)
            if notes_doc:
                notes_text = export_doc_text(drive_service, notes_doc["id"])
        except Exception:
            pass

        result.matched.append({
            "event": event,
            "transcript_doc": transcript_doc,
            "transcript_text": transcript_text,
            "notes_text": notes_text,
        })

    return result
