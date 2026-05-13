from __future__ import annotations

import re

from ..shared.convert import (
    compute_duration,
    format_participants,
    make_filename,
    parse_dt,
    yaml_escape,
)


def meeting_to_markdown(match: dict) -> str:
    event = match["event"]
    transcript_text = match.get("transcript_text", "")
    notes_text = match.get("notes_text", "")

    title = event.get("title") or "Untitled Meeting"
    meet_link = event.get("meet_link", "")
    organizer_email = event.get("organizer_email", "")
    calendar_link = event.get("calendar_link", "")

    date_obj = parse_dt(event.get("start", ""))
    date_str = date_obj.strftime("%Y-%m-%d") if date_obj else ""
    date_display = date_obj.strftime("%B %d, %Y") if date_obj else ""
    duration = compute_duration(event.get("start", ""), event.get("end", ""))

    attendees = event.get("attendees", [])
    participants = format_participants(attendees)
    participant_names = [a.get("name") or a.get("email", "") for a in attendees]

    segments = parse_transcript(transcript_text)

    lines: list[str] = []

    lines.append("---")
    lines.append(f'title: "{yaml_escape(title)}"')
    if date_str:
        lines.append(f"date: {date_str}")
    lines.append("type: gmeet-transcript")
    lines.append("source: google-meet")
    if meet_link:
        lines.append(f'meet_link: "{meet_link}"')
    if calendar_link:
        lines.append(f'calendar_event_url: "{calendar_link}"')
    lines.append("tags:")
    lines.append("  - gmeet-transcript")
    lines.append("  - meeting")
    if participants:
        lines.append("participants:")
        for p in participants:
            lines.append(f'  - "{yaml_escape(p)}"')
    if organizer_email:
        lines.append(f'organizer: "{yaml_escape(organizer_email)}"')
    if duration:
        lines.append(f'duration: "{duration}"')
    lines.append("---")
    lines.append("")

    lines.append(f"# {title}")
    lines.append("")
    header_parts = []
    if date_display:
        header_parts.append(f"**Date:** {date_display}")
    if duration:
        header_parts.append(f"**Duration:** {duration}")
    if participant_names:
        header_parts.append(f"**Participants:** {', '.join(participant_names)}")
    if organizer_email:
        organizer_display = event.get("organizer_name") or organizer_email
        header_parts.append(f"**Organizer:** {organizer_display}")
    if meet_link:
        short_link = meet_link.replace("https://", "")
        header_parts.append(f"**Meet link:** [{short_link}]({meet_link})")
    lines.extend(f"{p}  " for p in header_parts)
    lines.append("")

    if notes_text:
        lines.append("## Summary")
        lines.append("")
        lines.append(notes_text.strip())
        lines.append("")

    if segments:
        lines.append("## Transcript")
        lines.append("")
        for seg in segments:
            ts_part = f" ({seg['timestamp']})" if seg["timestamp"] else ""
            lines.append(f"**{seg['speaker']}**{ts_part}  ")
            lines.append(seg["text"])
            lines.append("")
    elif transcript_text.strip():
        lines.append("## Transcript")
        lines.append("")
        lines.append(transcript_text.strip())
        lines.append("")

    return "\n".join(lines)


def parse_transcript(text: str) -> list[dict]:
    if not text or not text.strip():
        return []

    segments: list[dict] = []
    lines = text.strip().split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        speaker_match = _is_speaker_line(line)
        if speaker_match and i + 1 < len(lines):
            speaker = line
            timestamp = ""
            text_start = i + 1

            next_line = lines[i + 1].strip()
            ts_match = _is_timestamp(next_line)
            if ts_match:
                timestamp = next_line
                text_start = i + 2

            text_lines = []
            j = text_start
            while j < len(lines):
                l = lines[j].strip()
                if not l:
                    j += 1
                    continue
                if _is_speaker_line(l):
                    break
                text_lines.append(l)
                j += 1

            if text_lines:
                segments.append({
                    "speaker": speaker,
                    "timestamp": _normalize_timestamp(timestamp),
                    "text": " ".join(text_lines),
                })
                i = j
                continue

        i += 1

    return segments


def gmeet_make_filename(event: dict) -> str:
    title = event.get("title") or "Untitled Meeting"
    date_obj = parse_dt(event.get("start", ""))
    date_str = date_obj.strftime("%Y-%m-%d") if date_obj else ""
    return make_filename(title, date_str)


def _is_speaker_line(line: str) -> bool:
    if not line or len(line) > 100:
        return False
    if re.match(r"^\d", line):
        return False
    if line.startswith(("- ", "* ", "#")):
        return False
    words = line.split()
    return 1 <= len(words) <= 6 and not line.endswith((".", "?", "!", ","))


def _is_timestamp(line: str) -> str:
    if re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", line.strip()):
        return line.strip()
    return ""


def _normalize_timestamp(ts: str) -> str:
    if not ts:
        return ""
    parts = ts.split(":")
    if len(parts) == 2:
        return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    return ts
