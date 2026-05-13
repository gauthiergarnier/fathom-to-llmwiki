from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Iterator
from datetime import datetime

import httpx

from .config import Config

log = logging.getLogger(__name__)

_MAX_RETRIES = 3


class FathomClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._http = httpx.Client(
            base_url=config.base_url,
            headers={"X-Api-Key": config.api_key},
            timeout=120.0,
        )
        self._request_times: deque[float] = deque()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> FathomClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _wait_for_rate_limit(self) -> None:
        now = time.monotonic()
        window = 60.0
        while self._request_times and (now - self._request_times[0]) > window:
            self._request_times.popleft()
        if len(self._request_times) >= self._config.rate_limit_per_minute:
            sleep_for = window - (now - self._request_times[0]) + 0.1
            log.debug("Rate limit: sleeping %.1fs", sleep_for)
            time.sleep(sleep_for)
        self._request_times.append(time.monotonic())

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        for attempt in range(1, _MAX_RETRIES + 1):
            self._wait_for_rate_limit()
            try:
                resp = self._http.request(method, path, **kwargs)
            except httpx.TransportError as e:
                if attempt == _MAX_RETRIES:
                    raise
                log.warning("Transport error (attempt %d/%d): %s", attempt, _MAX_RETRIES, e)
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 429:
                reset = resp.headers.get("RateLimit-Reset")
                sleep_for = float(reset) if reset else 2 ** attempt
                log.warning("Rate limited (429), sleeping %.1fs", sleep_for)
                time.sleep(sleep_for)
                continue

            if resp.status_code >= 500:
                if attempt == _MAX_RETRIES:
                    resp.raise_for_status()
                log.warning("Server error %d (attempt %d/%d)", resp.status_code, attempt, _MAX_RETRIES)
                time.sleep(2 ** attempt)
                continue

            resp.raise_for_status()
            return resp

        raise RuntimeError("Exhausted retries")

    def list_meetings(
        self,
        *,
        include_transcript: bool = True,
        include_summary: bool = True,
        include_action_items: bool = True,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        recorded_by: list[str] | None = None,
        invitee_domains: list[str] | None = None,
    ) -> Iterator[dict]:
        params: dict = {
            "include_transcript": str(include_transcript).lower(),
            "include_summary": str(include_summary).lower(),
            "include_action_items": str(include_action_items).lower(),
        }
        if created_after:
            params["created_after"] = created_after.isoformat()
        if created_before:
            params["created_before"] = created_before.isoformat()

        recorded_by_params: list[tuple[str, str]] = []
        if recorded_by:
            for email in recorded_by:
                recorded_by_params.append(("recorded_by[]", email))
        if invitee_domains:
            for domain in invitee_domains:
                recorded_by_params.append(("calendar_invitees_domains[]", domain))

        cursor: str | None = None
        while True:
            p = dict(params)
            if cursor:
                p["cursor"] = cursor
            all_params = list(p.items()) + recorded_by_params

            resp = self._request("GET", "/meetings", params=all_params)
            data = resp.json()

            for meeting in data.get("items", []):
                yield meeting

            cursor = data.get("next_cursor")
            if not cursor:
                break

    def get_transcript(self, recording_id: int) -> list[dict]:
        resp = self._request("GET", f"/recordings/{recording_id}/transcript")
        return resp.json().get("transcript", [])

    def get_summary(self, recording_id: int) -> dict | None:
        resp = self._request("GET", f"/recordings/{recording_id}/summary")
        return resp.json()
