from __future__ import annotations

import re
from datetime import datetime


def meeting_to_markdown(meeting: dict) -> str:
    title = meeting.get("title") or "Untitled Meeting"
    recording_url = meeting.get("url") or meeting.get("share_url") or ""
    created_at = meeting.get("created_at", "")
    rec_start = meeting.get("recording_start_time") or created_at
    rec_end = meeting.get("recording_end_time")

    date_obj = _parse_dt(rec_start)
    date_str = date_obj.strftime("%Y-%m-%d") if date_obj else ""
    date_display = date_obj.strftime("%B %d, %Y") if date_obj else ""
    duration = _compute_duration(rec_start, rec_end)

    recorded_by_obj = meeting.get("recorded_by") or {}
    recorded_by = recorded_by_obj.get("name", "")

    invitees = meeting.get("calendar_invitees") or []
    participants = _format_participants(invitees)
    participant_names = [i.get("name", i.get("email", "")) for i in invitees]

    transcript = meeting.get("transcript") or []
    summary_obj = meeting.get("default_summary") or {}
    summary_text = summary_obj.get("markdown_formatted", "")
    action_items = meeting.get("action_items") or []

    lines: list[str] = []

    # YAML frontmatter
    lines.append("---")
    lines.append(f'title: "{_yaml_escape(title)}"')
    if date_str:
        lines.append(f"date: {date_str}")
    lines.append("type: fathom-transcript")
    lines.append("source: fathom")
    if recording_url:
        lines.append(f'recording_url: "{recording_url}"')
    lines.append("tags:")
    lines.append("  - fathom-transcript")
    lines.append("  - meeting")
    if participants:
        lines.append("participants:")
        for p in participants:
            lines.append(f'  - "{_yaml_escape(p)}"')
    if recorded_by:
        lines.append(f'recorded_by: "{_yaml_escape(recorded_by)}"')
    if duration:
        lines.append(f'duration: "{duration}"')
    lines.append("---")
    lines.append("")

    # Header
    lines.append(f"# {title}")
    lines.append("")
    header_parts = []
    if date_display:
        header_parts.append(f"**Date:** {date_display}")
    if duration:
        header_parts.append(f"**Duration:** {duration}")
    if participant_names:
        header_parts.append(f"**Participants:** {', '.join(participant_names)}")
    if recorded_by:
        header_parts.append(f"**Recorded by:** {recorded_by}")
    if recording_url:
        header_parts.append(f"**Recording:** [View on Fathom]({recording_url})")
    lines.extend(f"{p}  " for p in header_parts)
    lines.append("")

    # Summary — rewrite external Fathom links to internal transcript anchors
    if summary_text:
        lines.append("## Summary")
        lines.append("")
        lines.append(_rewrite_fathom_links(summary_text.strip(), transcript))
        lines.append("")

    # Action items
    if action_items:
        lines.append("## Action Items")
        lines.append("")
        for item in action_items:
            desc = item.get("description", "")
            assignee = ""
            if a := item.get("assignee"):
                assignee = a.get("name") or a.get("email") or ""
            completed = item.get("completed", False)
            check = "x" if completed else " "
            suffix = f" ({assignee})" if assignee else ""
            lines.append(f"- [{check}] {desc}{suffix}")
        lines.append("")

    # Transcript — with anchors for internal links from the summary
    if transcript:
        lines.append("## Transcript")
        lines.append("")
        for segment in transcript:
            speaker = segment.get("speaker", {})
            name = speaker.get("display_name", "Unknown")
            timestamp = segment.get("timestamp", "")
            text = segment.get("text", "")
            ts_secs = _timestamp_to_seconds(timestamp)
            block_id = f" ^t-{ts_secs}" if ts_secs is not None else ""
            ts_part = f" ({timestamp})" if timestamp else ""
            lines.append(f"**{name}**{ts_part}  ")
            lines.append(f"{text}{block_id}")
            lines.append("")

    return "\n".join(lines)


def make_filename(meeting: dict) -> str:
    title = meeting.get("title") or "Untitled Meeting"
    rec_start = meeting.get("recording_start_time") or meeting.get("created_at", "")
    date_obj = _parse_dt(rec_start)
    date_prefix = date_obj.strftime("%Y-%m-%d") if date_obj else "undated"

    safe_title = _sanitize_filename(title)
    if len(safe_title) > 100:
        safe_title = safe_title[:100].rstrip()

    return f"{date_prefix} - {safe_title}.md"


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()


def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _compute_duration(start: str, end: str) -> str:
    s, e = _parse_dt(start), _parse_dt(end)
    if not s or not e:
        return ""
    delta = e - s
    total_secs = int(delta.total_seconds())
    if total_secs < 0:
        return ""
    h, rem = divmod(total_secs, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}min"
    return f"{m} min"


def _timestamp_to_seconds(ts: str) -> int | None:
    if not ts:
        return None
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return None
    return None


def _rewrite_fathom_links(summary: str, transcript: list[dict]) -> str:
    if not transcript:
        return summary

    ts_seconds = []
    for seg in transcript:
        s = _timestamp_to_seconds(seg.get("timestamp", ""))
        if s is not None:
            ts_seconds.append(s)

    def _replace_link(m: re.Match) -> str:
        label = m.group(1)
        url = m.group(2)
        ts_match = re.search(r"[?&]timestamp=([\d.]+)", url)
        if not ts_match:
            return m.group(0)
        target_secs = int(float(ts_match.group(1)))
        # Find the closest transcript anchor at or before this timestamp
        best = None
        for s in ts_seconds:
            if s <= target_secs:
                best = s
            else:
                break
        if best is None and ts_seconds:
            best = ts_seconds[0]
        if best is not None:
            return f"[{label}](#^t-{best})"
        return m.group(0)

    return re.sub(r"\[([^\]]*)\]\((https?://[^)]+)\)", _replace_link, summary)


def _format_participants(invitees: list[dict]) -> list[str]:
    result = []
    for inv in invitees:
        name = inv.get("name", "")
        email = inv.get("email", "")
        if name and email:
            result.append(f"{name} <{email}>")
        elif email:
            result.append(email)
        elif name:
            result.append(name)
    return result
