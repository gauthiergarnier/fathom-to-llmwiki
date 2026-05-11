from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from .config import Config
from .profile import Profile
from .state import SyncState
from .sync import export_single, run_sync


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging")
def main(verbose: bool) -> None:
    """Export Fathom meeting transcripts to LLM Wiki."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@main.command()
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="Export meetings after this date")
@click.option("--until", type=click.DateTime(formats=["%Y-%m-%d"]), help="Export meetings before this date")
@click.option("--profile", "profile_path", type=click.Path(exists=True, dir_okay=False), help="TOML profile for participant/title filters")
@click.option("--recorded-by", multiple=True, help="Only export meetings recorded by this email (repeatable)")
@click.option("--topic", multiple=True, help="Only export meetings whose title contains this keyword (repeatable)")
@click.option("--exclude", multiple=True, help="Skip meetings whose title contains this keyword (repeatable)")
@click.option("--force", is_flag=True, help="Re-export already exported meetings")
@click.option("--dry-run", is_flag=True, help="Preview without writing files")
@click.option("--limit", type=int, help="Max meetings to export per batch")
@click.option("--batch", type=int, default=None, help="Auto-loop in batches of N (e.g. --batch 25)")
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
    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    profile = None
    if profile_path:
        profile = Profile.load(Path(profile_path))
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


@main.command("list")
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="List meetings after this date")
@click.option("--until", type=click.DateTime(formats=["%Y-%m-%d"]), help="List meetings before this date")
@click.option("--profile", "profile_path", type=click.Path(exists=True, dir_okay=False), help="TOML profile to preview filtering")
def list_meetings(since: datetime | None, until: datetime | None, profile_path: str | None) -> None:
    """List available Fathom meetings."""
    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    from .client import FathomClient

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


@main.command()
@click.argument("recording_id", type=int)
def export(recording_id: int) -> None:
    """Export a single meeting by recording ID."""
    try:
        config = Config.from_env()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    filepath = export_single(config, recording_id)
    click.echo(f"Exported: {filepath}")


@main.command()
def status() -> None:
    """Show sync status."""
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


@main.command()
def reset() -> None:
    """Clear sync state (re-exports will be possible)."""
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
