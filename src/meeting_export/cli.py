from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from .shared.state import SyncState


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging")
def main(verbose: bool) -> None:
    """Export meeting transcripts to LLM Wiki."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


# ── Fathom ──────────────────────────────────────────────────────────────


@main.group()
def fathom() -> None:
    """Fathom meeting transcripts."""


@fathom.command()
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="Export meetings after this date")
@click.option("--until", type=click.DateTime(formats=["%Y-%m-%d"]), help="Export meetings before this date")
@click.option("--profile", "profile_path", type=click.Path(exists=True, dir_okay=False), help="TOML profile for filters")
@click.option("--recorded-by", multiple=True, help="Only meetings recorded by this email")
@click.option("--topic", multiple=True, help="Only meetings whose title contains this keyword")
@click.option("--exclude", multiple=True, help="Skip meetings whose title contains this keyword")
@click.option("--force", is_flag=True, help="Re-export already exported meetings")
@click.option("--dry-run", is_flag=True, help="Preview without writing files")
@click.option("--limit", type=int, help="Max meetings to export per batch")
@click.option("--batch", type=int, default=None, help="Auto-loop in batches of N")
def sync(
    since: datetime | None,
    until: datetime | None,
    profile_path: str | None,
    recorded_by: tuple[str, ...],
    topic: tuple[str, ...],
    exclude: tuple[str, ...],
    force: bool,
    dry_run: bool,
    limit: int | None,
    batch: int | None,
) -> None:
    """Fetch new meetings from Fathom and export as markdown."""
    from .fathom.config import Config
    from .fathom.profile import Profile
    from .fathom.sync import run_sync

    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    profile = Profile.load(Path(profile_path)) if profile_path else None
    if profile_path:
        click.echo(f"Using profile: {profile_path}")

    filter_kwargs: dict = {
        "recorded_by": list(recorded_by) or None,
        "title_filter": list(topic) or None,
        "title_exclude": list(exclude) or None,
        "profile": profile,
    }

    prefix = "[dry-run] " if dry_run else ""
    click.echo(f"{prefix}Syncing Fathom transcripts to {config.transcript_dir}")

    if batch:
        total_exported = 0
        total_skipped = 0
        batch_num = 0
        while True:
            batch_num += 1
            click.echo(f"\n--- Batch {batch_num} (up to {batch} meetings) ---")
            result = run_sync(config, since=since, until=until, force=force, dry_run=dry_run, limit=batch, **filter_kwargs)
            total_exported += result.exported
            total_skipped += result.skipped
            click.echo(f"Batch {batch_num}: {result.summary()}")
            if result.exported == 0:
                break
        click.echo(f"\nAll done: {total_exported} exported, {total_skipped} skipped across {batch_num} batch(es)")
    else:
        result = run_sync(config, since=since, until=until, force=force, dry_run=dry_run, limit=limit, **filter_kwargs)
        click.echo(f"Done: {result.summary()}")


@fathom.command("list")
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="List meetings after this date")
@click.option("--until", type=click.DateTime(formats=["%Y-%m-%d"]), help="List meetings before this date")
@click.option("--profile", "profile_path", type=click.Path(exists=True, dir_okay=False), help="TOML profile to preview filtering")
def fathom_list(since: datetime | None, until: datetime | None, profile_path: str | None) -> None:
    """List available Fathom meetings."""
    from .fathom.client import FathomClient
    from .fathom.config import Config
    from .fathom.profile import Profile

    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    profile = Profile.load(Path(profile_path)) if profile_path else None

    if since and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    with FathomClient(config) as client:
        state = SyncState(config.state_file)
        count = 0
        filtered = 0
        for meeting in client.list_meetings(
            include_transcript=False,
            include_summary=False,
            include_action_items=False,
            created_after=since,
            created_before=until,
        ):
            if profile and not profile.matches_meeting(meeting):
                filtered += 1
                continue
            rid = meeting.get("recording_id", "?")
            title = meeting.get("title", "Untitled")
            created = meeting.get("created_at", "")[:10]
            exported = " [exported]" if state.is_exported(rid) else ""
            click.echo(f"  {rid}  {created}  {title}{exported}")
            count += 1

    click.echo(f"\n{count} meeting(s) found" + (f", {filtered} filtered out" if filtered else ""))


@fathom.command()
@click.argument("recording_id", type=int)
def export(recording_id: int) -> None:
    """Export a single meeting by recording ID."""
    from .fathom.config import Config
    from .fathom.sync import export_single

    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    filepath = export_single(config, recording_id)
    click.echo(f"Exported: {filepath}")


@fathom.command()
def status() -> None:
    """Show Fathom sync status."""
    from .fathom.config import Config

    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    state = SyncState(config.state_file)
    last = state.last_sync_at
    click.echo(f"State file: {config.state_file}")
    click.echo(f"Output dir: {config.transcript_dir}")
    click.echo(f"Last sync:  {last.strftime('%Y-%m-%d %H:%M UTC') if last else 'never'}")
    click.echo(f"Exported:   {state.exported_count} meeting(s)")


@fathom.command()
def reset() -> None:
    """Clear Fathom sync state."""
    from .fathom.config import Config

    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    state = SyncState(config.state_file)
    if state.exported_count == 0:
        click.echo("State is already empty.")
        return

    if click.confirm(f"Reset state? ({state.exported_count} exported meetings will be forgotten)"):
        state.reset()
        click.echo("State cleared.")


# ── Google Meet ─────────────────────────────────────────────────────────


@main.group()
def gmeet() -> None:
    """Google Meet transcripts."""


@gmeet.command()
def auth() -> None:
    """Run OAuth flow and verify credentials."""
    from .gmeet.auth import get_credentials
    from .gmeet.config import Config

    try:
        config = Config.from_env()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        creds = get_credentials(config)
        click.echo("Authenticated successfully.")
        click.echo(f"Token saved to: {config.token_path}")
        click.echo(f"Scopes: {', '.join(creds.scopes or [])}")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Authentication failed: {e}", err=True)
        sys.exit(1)


@gmeet.command("sync")
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="Export meetings after this date")
@click.option("--until", type=click.DateTime(formats=["%Y-%m-%d"]), help="Export meetings before this date")
@click.option("--force", is_flag=True, help="Re-export already exported meetings")
@click.option("--dry-run", is_flag=True, help="Preview without writing files")
@click.option("--limit", type=int, help="Max meetings to export")
def gmeet_sync(
    since: datetime | None,
    until: datetime | None,
    force: bool,
    dry_run: bool,
    limit: int | None,
) -> None:
    """Fetch new meetings from Google Meet and export as markdown."""
    from .gmeet.config import Config
    from .gmeet.sync import run_sync

    try:
        config = Config.from_env()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    prefix = "[dry-run] " if dry_run else ""
    click.echo(f"{prefix}Syncing Google Meet transcripts to {config.transcript_dir}")

    result = run_sync(config, since=since, until=until, force=force, dry_run=dry_run, limit=limit)
    click.echo(f"Done: {result.summary()}")


@gmeet.command("list")
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="List meetings after this date")
@click.option("--until", type=click.DateTime(formats=["%Y-%m-%d"]), help="List meetings before this date")
@click.option("--limit", type=int, default=50, help="Max events to show")
def gmeet_list(since: datetime | None, until: datetime | None, limit: int) -> None:
    """List calendar events with Google Meet links."""
    from .gmeet.auth import build_calendar_service, get_credentials
    from .gmeet.calendar_client import list_meet_events
    from .gmeet.config import Config

    try:
        config = Config.from_env()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if since and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    if until and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=180)

    creds = get_credentials(config)
    cal_service = build_calendar_service(creds)
    state = SyncState(config.state_file)

    count = 0
    for event in list_meet_events(cal_service, since=since, until=until):
        eid = event.get("event_id", "?")
        title = event.get("title", "Untitled")
        start = event.get("start", "")[:10]
        exported = " [exported]" if state.is_exported(eid) else ""
        click.echo(f"  {start}  {title}{exported}")
        count += 1
        if count >= limit:
            break

    click.echo(f"\n{count} event(s) with Google Meet links")


@gmeet.command("status")
def gmeet_status() -> None:
    """Show Google Meet sync status."""
    from .gmeet.config import Config

    try:
        config = Config.from_env()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    state = SyncState(config.state_file)
    last = state.last_sync_at
    click.echo(f"State file: {config.state_file}")
    click.echo(f"Output dir: {config.transcript_dir}")
    click.echo(f"Last sync:  {last.strftime('%Y-%m-%d %H:%M UTC') if last else 'never'}")
    click.echo(f"Exported:   {state.exported_count} meeting(s)")


@gmeet.command("reset")
def gmeet_reset() -> None:
    """Clear Google Meet sync state."""
    from .gmeet.config import Config

    try:
        config = Config.from_env()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    state = SyncState(config.state_file)
    if state.exported_count == 0:
        click.echo("State is already empty.")
        return

    if click.confirm(f"Reset state? ({state.exported_count} exported meetings will be forgotten)"):
        state.reset()
        click.echo("State cleared.")
