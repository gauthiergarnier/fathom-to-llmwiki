from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..shared.io import atomic_write, resolve_collision
from ..shared.state import SyncState
from .auth import build_calendar_service, build_drive_service, get_credentials
from .calendar_client import list_meet_events
from .config import Config
from .converter import gmeet_make_filename, meeting_to_markdown
from .matcher import match_events_to_transcripts

log = logging.getLogger(__name__)


def run_sync(
    config: Config,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    force: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
) -> SyncResult:
    state = SyncState(config.state_file)
    result = SyncResult()

    if since is None:
        if state.last_sync_at:
            since = state.last_sync_at - timedelta(days=1)
        else:
            since = datetime.now(timezone.utc) - timedelta(days=180)

    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    config.transcript_dir.mkdir(parents=True, exist_ok=True)

    creds = get_credentials(config)
    cal_service = build_calendar_service(creds)
    drive_service = build_drive_service(creds)

    log.info("Fetching calendar events with Meet links...")
    candidates: list[dict] = []
    for event in list_meet_events(cal_service, since=since, until=until):
        event_id = event.get("event_id", "")
        title = event.get("title", "Untitled Meeting")

        if not force and state.is_exported(event_id):
            log.debug("Skipping already exported: %s", title)
            result.skipped += 1
            continue

        candidates.append(event)
        if limit is not None and len(candidates) >= limit:
            break

    log.info("Found %d new event(s) to check for transcripts", len(candidates))

    if not candidates:
        return result

    log.info("Searching Drive for transcripts...")
    match_result = match_events_to_transcripts(drive_service, candidates)

    result.no_transcript = len(match_result.no_transcript)
    result.errors = len(match_result.errors)

    for err_event, err_msg in match_result.errors:
        log.warning("Error for '%s': %s", err_event.get("title"), err_msg)

    for match in match_result.matched:
        event = match["event"]
        event_id = event.get("event_id", "")
        title = event.get("title", "Untitled Meeting")
        drive_doc_id = match.get("transcript_doc", {}).get("id", "")

        filename = gmeet_make_filename(event)
        filepath = config.transcript_dir / filename
        filepath = resolve_collision(filepath)
        rel_path = f"{config.output_subdir}/{filepath.name}"

        if not force and filepath.exists():
            log.debug("File already exists: %s", filepath)
            state.mark_exported(event_id, title, rel_path, drive_doc_id=drive_doc_id)
            result.skipped += 1
            continue

        markdown = meeting_to_markdown(match)

        if dry_run:
            log.info("[dry-run] Would export: %s -> %s", title, filepath.name)
            result.exported += 1
            continue

        atomic_write(filepath, markdown)
        state.mark_exported(event_id, title, rel_path, drive_doc_id=drive_doc_id)
        state.save()
        log.info("Exported: %s -> %s", title, filepath.name)
        result.exported += 1

    if not dry_run:
        state.save()

    return result


class SyncResult:
    def __init__(self) -> None:
        self.exported: int = 0
        self.skipped: int = 0
        self.no_transcript: int = 0
        self.errors: int = 0

    def summary(self) -> str:
        parts = [f"{self.exported} exported"]
        if self.skipped:
            parts.append(f"{self.skipped} skipped")
        if self.no_transcript:
            parts.append(f"{self.no_transcript} no transcript")
        if self.errors:
            parts.append(f"{self.errors} errors")
        return ", ".join(parts)
