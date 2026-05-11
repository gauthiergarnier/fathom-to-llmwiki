# Fathom to LLM Wiki

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://opensource.org/licenses/Apache-2.0)

Export [Fathom](https://fathom.video) meeting transcripts as structured Markdown files and feed them into an [LLM Wiki](https://github.com/gauthiergarnier/llmwiki-sqlite-vec) knowledge base.

Meetings turn into searchable, interlinked documents that Claude can read, cite, and build on — without copy-pasting transcripts or losing context between conversations.

## Why this exists

Fathom records your meetings and generates AI summaries and transcripts. LLM Wiki turns a folder of documents into a structured, searchable knowledge base that Claude can work with via MCP. This tool bridges the two: it pulls your meetings from the Fathom API, converts them to well-structured Markdown files with YAML frontmatter, and drops them into your LLM Wiki workspace where they get indexed automatically.

The result: every meeting you record becomes part of your knowledge base. Claude can search across them, cross-reference decisions with earlier conversations, and cite specific moments when writing wiki pages.

## What it does

1. **Fetches meetings** from the Fathom API — summaries, action items, transcripts, and metadata (participants, dates, duration).
2. **Converts to Markdown** — each meeting becomes a `.md` file with YAML frontmatter, an AI summary with internal links, action item checklists, and the full transcript.
3. **Links summary to transcript** — timestamps in the Fathom summary are rewritten to Obsidian block references (`^t-169`), so clicking a summary bullet jumps to the exact moment in the transcript.
4. **Tracks sync state** — a local JSON file records which meetings have been exported, so re-running the command only fetches new ones.
5. **Integrates with LLM Wiki** — files are written to your workspace directory. If the LLM Wiki server is running, the file watcher auto-indexes them. Otherwise, run `llmwiki reindex`.

## Output format

Each meeting produces a file like `2026-05-11 - Weekly Strategy Review.md`:

```markdown
---
title: "Weekly Strategy Review"
date: 2026-05-11
type: fathom-transcript
source: fathom
recording_url: "https://fathom.video/calls/123456"
tags:
  - fathom-transcript
  - meeting
participants:
  - "Alice Martin <alice@example.com>"
  - "Bob Chen <bob@partner.com>"
recorded_by: "Jane Smith"
duration: "45 min"
---

# Weekly Strategy Review

**Date:** May 11, 2026
**Duration:** 45 min
**Participants:** Alice Martin, Bob Chen
**Recorded by:** Jane Smith
**Recording:** [View on Fathom](https://fathom.video/calls/123456)

## Summary

[Key decision about Q3 roadmap.](#^t-332)
[Budget approved for the new initiative.](#^t-890)

## Action Items

- [ ] Send updated timeline (Alice Martin)
- [ ] Draft proposal outline (Bob Chen)

## Transcript

**Alice Martin** (00:05:32)
Let's revisit the budget allocations. ^t-332

**Bob Chen** (00:14:50)
I've updated the spreadsheet with the new figures. ^t-890
```

## Quick start

**Requirements:** Python 3.11+, a [Fathom API key](https://fathom.video) (Settings > API Access)

```bash
git clone https://github.com/gauthiergarnier/fathom-to-llmwiki.git
cd fathom-to-llmwiki

# Create a virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure your API key
cp .env.example .env
# Edit .env and set FATHOM_API_KEY=your_key_here
```

## Usage

### Sync meetings

Fetch new meetings from Fathom and export them as Markdown:

```bash
fathom-export sync
```

On the first run, this fetches meetings from the last 30 days. On subsequent runs, it picks up from where it left off.

**Options:**

| Flag | Description |
|------|-------------|
| `--since YYYY-MM-DD` | Export meetings after this date |
| `--until YYYY-MM-DD` | Export meetings before this date |
| `--profile PATH` | TOML profile for participant/title filtering (see [Profiles](#profiles)) |
| `--recorded-by EMAIL` | Only export meetings recorded by this person (repeatable) |
| `--topic KEYWORD` | Only export meetings whose title contains this keyword (repeatable) |
| `--exclude KEYWORD` | Skip meetings whose title contains this keyword (repeatable) |
| `--force` | Re-export already exported meetings |
| `--dry-run` | Preview what would be exported without writing files |
| `--limit N` | Max number of meetings to export per batch |
| `--batch N` | Auto-loop in batches of N until all meetings are exported |

**Examples:**

```bash
# Backfill all meetings from 2025 in batches of 25
fathom-export sync --since 2025-01-01 --batch 25

# Export only meetings with customers
fathom-export sync --profile profiles/customers.toml --batch 25

# Export only internal team meetings
fathom-export sync --profile profiles/team.toml --since 2026-01-01

# Preview what a profile would export
fathom-export list --profile profiles/customers.toml

# Combine profile with date range
fathom-export sync --profile profiles/customers.toml --since 2026-01-01 --until 2026-03-31 --batch 25

# Ad-hoc filters (without a profile)
fathom-export sync --recorded-by alice@example.com --topic "Strategy"

# Re-export everything (e.g., after a format change)
fathom-export reset
fathom-export sync --since 2025-01-01 --batch 25
```

### List meetings

See what meetings are available in Fathom without exporting:

```bash
fathom-export list
fathom-export list --since 2026-05-01
```

Meetings already exported are marked with `[exported]`.

### Export a single meeting

Export one specific meeting by its recording ID (shown by `list`):

```bash
fathom-export export 145162043
```

### Check sync status

```bash
fathom-export status
```

Shows the last sync time, number of exported meetings, and output directory.

### Reset sync state

```bash
fathom-export reset
```

Clears the sync state file so all meetings can be re-exported. Does not delete any exported files.

### Verbose mode

Add `-v` before any command for debug-level logging:

```bash
fathom-export -v sync --limit 3
```

## Configuration

All configuration is via environment variables, loaded from a `.env` file in the project directory.

| Variable | Default | Description |
|----------|---------|-------------|
| `FATHOM_API_KEY` | *(required)* | Your Fathom API key |
| `FATHOM_BASE_URL` | `https://api.fathom.ai/external/v1` | API base URL |
| `OUTPUT_DIR` | *(your home directory)* | Root of your LLM Wiki workspace |
| `OUTPUT_SUBDIR` | `Fathom Transcripts` | Subdirectory for exported files |
| `STATE_FILE` | `.fathom-export-state.json` | Path to the sync state file |
| `RATE_LIMIT_PER_MINUTE` | `50` | Max API requests per minute (Fathom allows 60) |
| `RECORDED_BY` | *(none)* | Comma-separated emails to filter by recorder |
| `TITLE_FILTER` | *(none)* | Comma-separated keywords — only export matching titles |
| `TITLE_EXCLUDE` | *(none)* | Comma-separated keywords — skip matching titles |

Filters set in `.env` act as defaults. CLI flags (`--recorded-by`, `--topic`, `--exclude`) override them when provided.

## Profiles

For recurring exports, create TOML profile files instead of passing filters every time. A profile defines which meetings to export based on **participants** (by email, name, or company domain) and optionally **title keywords**.

```bash
fathom-export sync --profile profiles/team.toml --batch 25
fathom-export sync --profile profiles/customers.toml --since 2025-01-01 --batch 25
```

### Profile format

```toml
# profiles/customers.toml
[participants]
include = [
    "*@customer-one.com",    # domain wildcard — any email at this domain
    "*@partner-corp.io",     # another company domain
    "jane.doe@external.com", # specific email address
    "Alice Martin",          # name substring match
]
exclude = [
    "noreply@customer-one.com",  # skip automated invites
]

[title]
include = ["Strategy", "Review"]   # optional: only matching titles
exclude = ["Interview", "1:1"]     # optional: skip matching titles
```

### Matching rules

- **`*@domain.com`** — matches any email at that domain (most common pattern)
- **`user@domain.com`** — exact email match
- **`Name`** — substring match against participant names (case-insensitive)
- A meeting matches if **any** participant matches an `include` pattern and **none** of the matching participants are in `exclude`
- When all include patterns are domain wildcards (`*@...`), the domains are also sent to the Fathom API for server-side pre-filtering

### Example profiles

Two example profiles are provided in `profiles/`:

- **[`team.example.toml`](profiles/team.example.toml)** — internal team meetings (filter by your company domains)
- **[`customers.example.toml`](profiles/customers.example.toml)** — customer and partner meetings (filter by external domains)

Copy and customize them:

```bash
cp profiles/team.example.toml profiles/team.toml
cp profiles/customers.example.toml profiles/customers.toml
# Edit with your actual domains and contacts
```

The `list` command also accepts `--profile` to preview what a profile would match:

```bash
fathom-export list --profile profiles/customers.toml --since 2026-01-01
```

## Integration with LLM Wiki

This tool is designed as a companion to [llmwiki-sqlite-vec](https://github.com/gauthiergarnier/llmwiki-sqlite-vec). Set `OUTPUT_DIR` to your LLM Wiki workspace directory and exported transcripts become searchable sources.

**If the LLM Wiki server is running** (`llmwiki serve`), the file watcher auto-detects new `.md` files and indexes them into the SQLite database (FTS5 full-text + vector embeddings).

**If the server is not running**, reindex after export:

```bash
llmwiki reindex /path/to/your/workspace
```

Once indexed, Claude can search across your meeting transcripts via MCP, cite specific moments in wiki pages, and cross-reference decisions across meetings.

### Obsidian compatibility

Exported files are standard Markdown with YAML frontmatter and work in [Obsidian](https://obsidian.md) out of the box. Summary links use Obsidian block references (`[text](#^t-332)` pointing to `^t-332` in the transcript), so clicking a summary point scrolls to the relevant transcript moment.

### Automation with cron

For daily automatic sync, add a cron job:

```bash
crontab -e
```

```cron
0 7 * * * cd /path/to/fathom-to-llmwiki && /path/to/.venv/bin/fathom-export sync >> /tmp/fathom-export.log 2>&1
```

## How it works

The sync runs in two phases to minimize API usage:

1. **Discovery** — calls `GET /meetings` with summary and action items included (small payloads), paginates through results, and filters out already-exported meetings.
2. **Export** — for each new meeting, fetches the full transcript via `GET /recordings/{id}/transcript`, converts everything to Markdown, and writes the file atomically (temp file + rename, safe for iCloud/Dropbox sync).

The Fathom API has a global rate limit of 60 requests per 60 seconds. The client tracks request timestamps and sleeps proactively to stay under the configured limit (default: 50/min). On HTTP 429, it reads the `RateLimit-Reset` header and backs off automatically.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
