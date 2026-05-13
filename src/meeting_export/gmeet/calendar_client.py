from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterator

from googleapiclient.discovery import Resource

log = logging.getLogger(__name__)


def list_meet_events(
    service: Resource,
    *,
    since: datetime,
    until: datetime | None = None,
) -> Iterator[dict]:
    kwargs: dict = {
        "calendarId": "primary",
        "timeMin": since.isoformat(),
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 250,
    }
    if until:
        kwargs["timeMax"] = until.isoformat()

    page_token = None
    while True:
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.events().list(**kwargs).execute()

        log.debug("API returned %d events", len(response.get("items", [])))
        for event in response.get("items", []):
            log.debug(
                "Event: %s | start=%s | conf=%s",
                event.get("summary", "?"),
                event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "?")),
                bool(event.get("conferenceData")),
            )
            conf = event.get("conferenceData")
            if not conf:
                log.debug("No conferenceData: %s", event.get("summary", "?"))
                continue
            solution = conf.get("conferenceSolution", {})
            sol_name = solution.get("name", "")
            if sol_name != "Google Meet":
                log.debug(
                    "Skipped (solution=%r): %s",
                    sol_name,
                    event.get("summary", "?"),
                )
                continue

            yield _extract_event(event)

        page_token = response.get("nextPageToken")
        if not page_token:
            break


def _extract_event(event: dict) -> dict:
    conf = event.get("conferenceData", {})
    meet_link = ""
    for ep in conf.get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            meet_link = ep.get("uri", "")
            break

    start = event.get("start", {})
    end = event.get("end", {})

    attendees = []
    for att in event.get("attendees", []):
        attendees.append({
            "email": att.get("email", ""),
            "name": att.get("displayName", ""),
            "response_status": att.get("responseStatus", ""),
            "self": att.get("self", False),
        })

    organizer = event.get("organizer", {})

    notes_attachment = None
    recording_attachment = None
    for att in event.get("attachments", []):
        mime = att.get("mimeType", "")
        title = att.get("title", "")
        if mime == "application/vnd.google-apps.document":
            if notes_attachment is None or "Gemini" in title:
                notes_attachment = {
                    "file_id": att.get("fileId", ""),
                    "title": title,
                    "url": att.get("fileUrl", ""),
                }
        elif mime.startswith("video/"):
            recording_attachment = {
                "file_id": att.get("fileId", ""),
                "title": title,
                "url": att.get("fileUrl", ""),
            }

    return {
        "event_id": event.get("id", ""),
        "title": event.get("summary", "Untitled Meeting"),
        "start": start.get("dateTime", start.get("date", "")),
        "end": end.get("dateTime", end.get("date", "")),
        "attendees": attendees,
        "organizer_email": organizer.get("email", ""),
        "organizer_name": organizer.get("displayName", ""),
        "meet_link": meet_link,
        "conference_id": conf.get("conferenceId", ""),
        "calendar_link": event.get("htmlLink", ""),
        "notes_attachment": notes_attachment,
        "recording_attachment": recording_attachment,
    }
