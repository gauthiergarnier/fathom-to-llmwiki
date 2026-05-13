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

        for event in response.get("items", []):
            conf = event.get("conferenceData")
            if not conf:
                continue
            solution = conf.get("conferenceSolution", {})
            if solution.get("name") != "Google Meet":
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
    }
