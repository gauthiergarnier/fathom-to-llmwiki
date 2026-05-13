from __future__ import annotations

import logging
from datetime import datetime, timedelta

from googleapiclient.discovery import Resource

log = logging.getLogger(__name__)

TRANSCRIPT_MIME = "application/vnd.google-apps.document"


def find_transcript(
    service: Resource,
    event_title: str,
    event_date: datetime,
) -> dict | None:
    safe_title = _escape_query(event_title)

    query = (
        f"mimeType='{TRANSCRIPT_MIME}' "
        f"and name contains 'Transcript' "
        f"and name contains '{safe_title}' "
        f"and trashed = false"
    )
    results = _search(service, query, max_results=5)
    if results:
        return _best_match(results, event_date)

    day_start = event_date.strftime("%Y-%m-%dT00:00:00")
    day_end = (event_date + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59")
    query = (
        f"mimeType='{TRANSCRIPT_MIME}' "
        f"and name contains 'Transcript' "
        f"and modifiedTime >= '{day_start}' "
        f"and modifiedTime <= '{day_end}' "
        f"and trashed = false"
    )
    results = _search(service, query, max_results=10)
    if results:
        return _best_match(results, event_date)

    return None


def find_meeting_notes(
    service: Resource,
    event_title: str,
    event_date: datetime,
) -> dict | None:
    safe_title = _escape_query(event_title)
    query = (
        f"mimeType='{TRANSCRIPT_MIME}' "
        f"and name contains 'Notes' "
        f"and name contains '{safe_title}' "
        f"and trashed = false"
    )
    results = _search(service, query, max_results=5)
    if results:
        return _best_match(results, event_date)
    return None


def export_doc_text(service: Resource, file_id: str) -> str:
    content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return str(content)


def _search(service: Resource, query: str, max_results: int = 10) -> list[dict]:
    response = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name, modifiedTime, createdTime)",
            pageSize=max_results,
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    return response.get("files", [])


def _best_match(files: list[dict], event_date: datetime) -> dict:
    if len(files) == 1:
        return files[0]

    best = files[0]
    best_delta = float("inf")

    for f in files:
        modified = f.get("modifiedTime", "")
        if modified:
            try:
                mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                delta = abs((mod_dt - event_date).total_seconds())
                if delta < best_delta:
                    best_delta = delta
                    best = f
            except ValueError:
                continue

    return best


def _escape_query(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")
