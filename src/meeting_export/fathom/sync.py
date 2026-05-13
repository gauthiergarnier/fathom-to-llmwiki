from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..shared.io import atomic_write, resolve_collision
from ..shared.state import SyncState
from .client import FathomClient
from .config import Config
from .converter import fathom_make_filename, meeting_to_markdown
from .profile import Profile

log = logging.getLogger(__name__)


def run_sync(
    config: Config,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    force: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
    recorded_by: list[str] | None = None,
    title_filter: list[str] | None = None,
    title_exclude: list[str] | None = None,
    profile: Profile | None = None,
) -> SyncResult:
    state = SyncState(config.state_file)
    result = SyncResult()

    if since is None:
        if state.last_sync_at:
            since = state.last_sync_at - timedelta(days=1)
        else:
            since = datetime.now(timezone.utc) - timedelta(days=30)

    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    effective_recorded_by = recorded_by or config.recorded_by or None
    effective_title_filter = title_filter or config.title_filter or None
    effective_title_exclude = title_exclude or config.title_exclude or None

    api_domains = profile.api_domains if profile else None

    config.transcript_dir.mkdir(parents=True, exist_ok=True)

    with FathomClient(config) as client:
        log.info("Fetching meeting list...")
        candidates: list[dict] = []
        for meeting in client.list_meetings(
            include_transcript=False,
            include_summary=True,
            include_action_items=True,
            created_after=since,
            created_before=until,
            recorded_by=effective_recorded_by,
            invitee_domains=api_domains,
        ):
            recording_id = meeting.get("recording_id", "")
            title = meeting.get("title") or "Untitled Meeting"

            if not force and state.is_exported(recording_id):
                log.debug("Skipping already exported: %s", title)
                result.skipped += 1
                continue

            if not _title_matches(title, effective_title_filter, effective_title_exclude):
                log.debug("Filtered out by title: %s", title)
                result.filtered += 1
                continue

            if profile and not profile.matches_meeting(meeting):
                log.debug("Filtered out by profile: %s", title)
                result.filtered += 1
                continue

            candidates.append(meeting)
            if limit is not None and len(candidates) >= limit:
                break

        log.info("Found %d new meeting(s) to export", len(candidates))

        for meeting in candidates:
            recording_id = meeting.get("recording_id", "")
            title = meeting.get("title") or "Untitled Meeting"

            log.info("Fetching transcript for '%s'...", title)
            try:
                transcript = client.get_transcript(recording_id)
            except Exception as e:
                log.warning("Failed to fetch transcript for '%s': %s", title, e)
                result.errors += 1
                continue

            if not transcript:
                log.info("No transcript yet for '%s' (id=%s), skipping", title, recording_id)
                result.no_transcript += 1
                continue

            meeting["transcript"] = transcript

            filename = fathom_make_filename(meeting)
            filepath = config.transcript_dir / filename
            filepath = resolve_collision(filepath)
            rel_path = f"{config.output_subdir}/{filepath.name}"

            if not force and filepath.exists():
                log.debug("File already exists: %s", filepath)
                state.mark_exported(recording_id, title, rel_path)
                result.skipped += 1
                continue

            markdown = meeting_to_markdown(meeting)

            if dry_run:
                log.info("[dry-run] Would export: %s -> %s", title, filepath.name)
                result.exported += 1
                continue

            atomic_write(filepath, markdown)
            state.mark_exported(recording_id, title, rel_path)
            state.save()
            log.info("Exported: %s -> %s", title, filepath.name)
            result.exported += 1

    if not dry_run:
        state.save()

    return result


def export_single(config: Config, recording_id: int) -> Path:
    config.transcript_dir.mkdir(parents=True, exist_ok=True)

    with FathomClient(config) as client:
        transcript = client.get_transcript(recording_id)
        summary = client.get_summary(recording_id)

        meeting: dict = {
            "recording_id": recording_id,
            "transcript": transcript,
        }
        if summary:
            meeting["default_summary"] = summary

        for m in client.list_meetings(include_transcript=False, include_summary=False, include_action_items=False):
            if m.get("recording_id") == recording_id:
                meeting.update({k: v for k, v in m.items() if k not in ("transcript", "default_summary")})
                break

        filename = fathom_make_filename(meeting)
        filepath = config.transcript_dir / filename
        filepath = resolve_collision(filepath)
        markdown = meeting_to_markdown(meeting)
        atomic_write(filepath, markdown)

        state = SyncState(config.state_file)
        title = meeting.get("title", "")
        state.mark_exported(recording_id, title, f"{config.output_subdir}/{filepath.name}")
        state.save()

        return filepath


def _title_matches(
    title: str,
    include: list[str] | None,
    exclude: list[str] | None,
) -> bool:
    lower = title.lower()
    if include:
        if not any(kw.lower() in lower for kw in include):
            return False
    if exclude:
        if any(kw.lower() in lower for kw in exclude):
            return False
    return True


class SyncResult:
    def __init__(self) -> None:
        self.exported: int = 0
        self.skipped: int = 0
        self.filtered: int = 0
        self.no_transcript: int = 0
        self.errors: int = 0

    def summary(self) -> str:
        parts = [f"{self.exported} exported"]
        if self.skipped:
            parts.append(f"{self.skipped} skipped")
        if self.filtered:
            parts.append(f"{self.filtered} filtered out")
        if self.no_transcript:
            parts.append(f"{self.no_transcript} pending transcript")
        if self.errors:
            parts.append(f"{self.errors} errors")
        return ", ".join(parts)
