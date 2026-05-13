# Meeting Export

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://opensource.org/licenses/Apache-2.0)

Export meeting transcripts from **Fathom** and **Google Meet** as structured Markdown files for an [LLM Wiki](https://github.com/gauthiergarnier/llmwiki-sqlite-vec) knowledge base.

Meetings become searchable, interlinked documents that Claude can read, cite, and build on — without copy-pasting transcripts or losing context between conversations.

## How it works

```
meeting-export fathom sync    →  Fathom API  →  Markdown + YAML frontmatter
meeting-export gmeet sync     →  Calendar + Drive APIs  →  Markdown + YAML frontmatter
                                                              ↓
                                                    Obsidian / LLM Wiki vault
```

**Fathom** — pulls meetings from the Fathom API with AI summaries, action items, and full transcripts. Summary timestamps are rewritten to Obsidian block references for click-to-jump navigation.

**Google Meet** — reads your Google Calendar for events with Meet links, then retrieves the associated notes directly from event attachments:
- **Gemini Notes** — AI-generated summaries with structured sections (Summary, Decisions, Next Steps, Details)
- **Manual Notes** — rolling Google Docs with date-headed sections; only the section matching the event date is extracted
- Events without notes or recordings are skipped

Both connectors track sync state in a JSON file, so re-running only fetches new meetings.

## Quick start

**Requirements:** Python 3.11+

```bash
git clone https://github.com/gauthiergarnier/meeting-export.git
cd meeting-export

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env — set at minimum FATHOM_API_KEY or Google OAuth credentials
```

### Google Meet setup

1. Create an OAuth 2.0 Desktop App in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Enable **Google Calendar API** and **Google Drive API**
3. Add scopes: `calendar.readonly`, `drive.readonly`
4. Download the client secret JSON to `credentials/client_secret.json`
5. Run the auth flow:

```bash
meeting-export gmeet auth
```

## Usage

### Fathom

```bash
# Sync new meetings (incremental)
meeting-export fathom sync

# Backfill from a date in batches
meeting-export fathom sync --since 2025-01-01 --batch 25

# Filter by profile
meeting-export fathom sync --profile profiles/customers.toml --batch 25

# Ad-hoc filters
meeting-export fathom sync --recorded-by alice@example.com --topic "Strategy"

# List available meetings
meeting-export fathom list --since 2026-01-01

# Export a single meeting by ID
meeting-export fathom export 145162043

# Check sync state / reset
meeting-export fathom status
meeting-export fathom reset
```

### Google Meet

```bash
# Authenticate (first time only)
meeting-export gmeet auth

# Sync today's meetings
meeting-export gmeet sync --since 2026-05-13 --until 2026-05-14

# Sync last 6 months (default if no --since)
meeting-export gmeet sync

# Preview without writing files
meeting-export gmeet sync --dry-run

# List calendar events with Meet links
meeting-export gmeet list --since 2026-05-01

# Check sync state / reset
meeting-export gmeet status
meeting-export gmeet reset
```

### Common flags

| Flag | Description |
|------|-------------|
| `-v` / `--verbose` | Debug-level logging (place before subcommand) |
| `--since YYYY-MM-DD` | Export meetings after this date |
| `--until YYYY-MM-DD` | Export meetings before this date |
| `--force` | Re-export already exported meetings |
| `--dry-run` | Preview without writing files or updating state |
| `--limit N` | Max meetings to export |

Fathom-specific: `--profile`, `--recorded-by`, `--topic`, `--exclude`, `--batch N`

## Output format

Each meeting produces a file like `2026-05-13 - Weekly Strategy Review.md`:

```markdown
---
title: "Weekly Strategy Review"
date: 2026-05-13
type: gmeet-transcript
source: google-meet
meet_link: "https://meet.google.com/abc-defg-hij"
tags:
  - gmeet-transcript
  - meeting
participants:
  - "Alice Martin <alice@example.com>"
  - "Bob Chen <bob@partner.com>"
organizer: "alice@example.com"
duration: "45 min"
---

# Weekly Strategy Review

**Date:** May 13, 2026
**Duration:** 45 min
**Participants:** Alice Martin, Bob Chen

## Summary

Discussion covered Q3 roadmap priorities and budget allocation.

## Decisions

- Budget approved for the new initiative.

## Next Steps

- [Alice Martin] Send updated timeline by Friday.
- [Bob Chen] Draft proposal outline.
```

Fathom exports include additional sections: **Action Items** (checkbox list with assignees) and **Transcript** (full text with speaker names, timestamps, and Obsidian block anchors).

## Configuration

All configuration is via environment variables, loaded from `.env`.

### Shared

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | *(home directory)* | Root of your LLM Wiki workspace |

### Fathom

| Variable | Default | Description |
|----------|---------|-------------|
| `FATHOM_API_KEY` | *(required)* | Your Fathom API key |
| `FATHOM_BASE_URL` | `https://api.fathom.ai/external/v1` | API base URL |
| `FATHOM_OUTPUT_SUBDIR` | `Fathom Transcripts` | Subdirectory for Fathom exports |
| `FATHOM_STATE_FILE` | `.fathom-export-state.json` | Sync state file |
| `RATE_LIMIT_PER_MINUTE` | `50` | Max API requests per minute |

### Google Meet

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLIENT_SECRET` | `credentials/client_secret.json` | OAuth client secret path |
| `GOOGLE_TOKEN_PATH` | `~/.gmeet-to-llmwiki/token.json` | OAuth token storage |
| `GMEET_OUTPUT_SUBDIR` | `Google Meet Transcripts` | Subdirectory for GMeet exports |
| `GMEET_STATE_FILE` | `.gmeet-export-state.json` | Sync state file |

## Profiles (Fathom)

TOML files for recurring export filters based on participants and title keywords:

```toml
# profiles/customers.toml
[participants]
include = ["*@customer.com", "jane.doe@partner.io"]
exclude = ["noreply@customer.com"]

[title]
include = ["Strategy", "Review"]
exclude = ["Interview"]
```

```bash
meeting-export fathom sync --profile profiles/customers.toml --batch 25
```

Matching rules:
- `*@domain.com` — any email at that domain
- `user@domain.com` — exact email match
- `Name` — substring match against participant names (case-insensitive)

Example profiles in `profiles/*.example.toml`.

## Integration with LLM Wiki

Set `OUTPUT_DIR` to your LLM Wiki workspace. Exported files are auto-indexed by the file watcher if the server is running, or reindex manually with `llmwiki reindex`.

Files are standard Markdown with YAML frontmatter and work in [Obsidian](https://obsidian.md) out of the box.

### Automation

```cron
# Daily sync at 7am
0 7 * * * cd /path/to/meeting-export && .venv/bin/meeting-export fathom sync >> /tmp/meeting-export.log 2>&1
0 7 * * * cd /path/to/meeting-export && .venv/bin/meeting-export gmeet sync >> /tmp/meeting-export.log 2>&1
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
