from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    participant_include: list[str] = field(default_factory=list)
    participant_exclude: list[str] = field(default_factory=list)
    title_include: list[str] = field(default_factory=list)
    title_exclude: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Profile:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        participants = data.get("participants", {})
        title = data.get("title", {})

        return cls(
            participant_include=participants.get("include", []),
            participant_exclude=participants.get("exclude", []),
            title_include=title.get("include", []),
            title_exclude=title.get("exclude", []),
        )

    def matches_meeting(self, meeting: dict) -> bool:
        title = meeting.get("title") or ""
        if not self._title_matches(title):
            return False
        if not self.participant_include:
            return True
        invitees = meeting.get("calendar_invitees") or []
        return self._any_participant_matches(invitees)

    def _title_matches(self, title: str) -> bool:
        lower = title.lower()
        if self.title_include:
            if not any(kw.lower() in lower for kw in self.title_include):
                return False
        if self.title_exclude:
            if any(kw.lower() in lower for kw in self.title_exclude):
                return False
        return True

    def _any_participant_matches(self, invitees: list[dict]) -> bool:
        for inv in invitees:
            email = (inv.get("email") or "").lower()
            name = (inv.get("name") or "").lower()
            if self._matches_any_pattern(email, name, self.participant_include):
                if not self._matches_any_pattern(email, name, self.participant_exclude):
                    return True
        return False

    @staticmethod
    def _matches_any_pattern(email: str, name: str, patterns: list[str]) -> bool:
        for pattern in patterns:
            p = pattern.lower()
            if "@" in p:
                if fnmatch.fnmatch(email, p):
                    return True
            else:
                if p in name or p in email:
                    return True
        return False

    @property
    def api_domains(self) -> list[str] | None:
        domains = []
        for p in self.participant_include:
            if p.startswith("*@") and "*" not in p[2:] and "?" not in p[2:]:
                domains.append(p[2:])
        if domains and len(domains) == len(self.participant_include):
            return domains
        return None
