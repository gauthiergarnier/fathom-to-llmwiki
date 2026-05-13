# Requirements: Meeting Export

A CLI tool that extracts meeting transcripts and notes from multiple sources (Fathom, Google Meet) and converts them to structured markdown files for ingestion into an LLM Wiki knowledge base (Obsidian vault).

## Glossary

- **Connector**: A source-specific module that fetches meeting data from an external service (e.g., Fathom API, Google Calendar + Drive APIs).
- **Sync**: The process of fetching new meetings since the last run, converting them, and writing markdown files.
- **SyncState**: A JSON file tracking which meetings have already been exported, enabling incremental syncs.
- **Profile**: A TOML file defining participant and title filters for selective export (Fathom only).
- **Gemini Notes**: AI-generated meeting summaries created by Google Gemini, stored as Google Docs and attached to calendar events.
- **Manual Notes**: Human-written meeting notes stored in a rolling Google Doc with date-headed sections for each occurrence.
- **YAML Frontmatter**: Structured metadata block at the top of each markdown file, enabling search and filtering in Obsidian.

## Requirements

### 1. Multi-Source Meeting Export

**As a** knowledge worker,
**I want** to export meeting transcripts from multiple sources into a single knowledge base,
**so that** all my meeting notes are searchable and accessible in one place.

**Acceptance Criteria:**

- 1.1: WHEN the user runs `meeting-export fathom sync`, THE system SHALL fetch meetings from the Fathom API and write markdown files to the configured output directory.
- 1.2: WHEN the user runs `meeting-export gmeet sync`, THE system SHALL fetch calendar events with Google Meet links, retrieve associated notes from Google Drive, and write markdown files to the configured output directory.
- 1.3: WHILE a connector is syncing, THE system SHALL skip meetings that have already been exported (tracked via SyncState) unless `--force` is specified.

### 2. Incremental Sync

**As a** user running the tool regularly,
**I want** each sync to pick up only new meetings since the last run,
**so that** I don't re-process or duplicate content.

**Acceptance Criteria:**

- 2.1: WHEN no `--since` flag is provided, THE system SHALL default to syncing from the last sync timestamp (minus 1 day overlap) or the last 180 days for first run.
- 2.2: WHEN a meeting is successfully exported, THE system SHALL record its ID, title, file path, and export timestamp in the SyncState JSON file.
- 2.3: WHEN a meeting ID is found in SyncState and `--force` is not set, THE system SHALL skip that meeting without re-fetching its content.
- 2.4: WHEN `--force` is specified, THE system SHALL re-export all meetings in the date range regardless of SyncState.

### 3. Fathom Connector

**As a** Fathom user,
**I want** to export my Fathom meeting recordings with their AI summaries, action items, and full transcripts,
**so that** I can reference them in my knowledge base.

**Acceptance Criteria:**

- 3.1: WHEN syncing from Fathom, THE system SHALL authenticate using the `FATHOM_API_KEY` environment variable.
- 3.2: WHEN a Fathom meeting has a summary, THE system SHALL include it with internal timestamp links rewritten to Obsidian block references (`^t-<seconds>`).
- 3.3: WHEN a Fathom meeting has action items, THE system SHALL render them as a checkbox list with assignee names.
- 3.4: WHEN a Fathom meeting has a transcript, THE system SHALL render it with speaker names, timestamps, and block anchors for cross-referencing.
- 3.5: WHERE a `--profile` TOML file is specified, THE system SHALL filter meetings by participant email patterns and title keywords defined in the profile.
- 3.6: WHERE `--recorded-by`, `--topic`, or `--exclude` flags are specified, THE system SHALL filter meetings by recording author email, title inclusion keywords, or title exclusion keywords respectively.
- 3.7: WHERE `--batch N` is specified, THE system SHALL process meetings in groups of N, looping until no new meetings are found.

### 4. Google Meet Connector

**As a** Google Workspace user,
**I want** to export Gemini-generated meeting notes and manual meeting notes from my Google Meet calls,
**so that** my meeting context is preserved in my knowledge base.

**Acceptance Criteria:**

- 4.1: WHEN the user runs `meeting-export gmeet auth`, THE system SHALL execute an OAuth 2.0 desktop flow for Google Calendar (readonly) and Drive (readonly) scopes, and persist the token to disk.
- 4.2: WHEN syncing from Google Meet, THE system SHALL query the user's primary Google Calendar for events that have Google Meet conference data.
- 4.3: WHEN a calendar event has a Google Doc attachment (notes or transcript), THE system SHALL use the attachment's `fileId` directly to export the document content — not search Drive by title.
- 4.4: WHEN the attached document is Gemini-generated (attachment title contains "Gemini"), THE system SHALL clean the raw text by removing the header block (title, date, invitees, attachments metadata) and Gemini feedback UI prompts, then render structured sections (Summary, Decisions, Next Steps, Details).
- 4.5: WHEN the attached document is a manual rolling notes doc (attachment title does not contain "Gemini"), THE system SHALL extract only the section matching the event date using date-header pattern matching (`Month DD, YYYY |`).
- 4.6: IF the manual notes section for the event date is empty (contains only structural headers and blank bullets), THEN THE system SHALL treat the event as having no transcript and skip export.
- 4.7: IF a calendar event has no document attachment, THEN THE system SHALL report it as "no transcript" and not attempt a Drive search.

### 5. Markdown Output Format

**As a** knowledge base consumer,
**I want** exported files to follow a consistent markdown structure with YAML frontmatter,
**so that** they are indexable, searchable, and renderable in Obsidian.

**Acceptance Criteria:**

- 5.1: WHEN exporting a meeting, THE system SHALL generate a markdown file with YAML frontmatter containing: title, date, type, source, tags, participants, and connector-specific fields (recording_url, meet_link, organizer, duration).
- 5.2: WHEN exporting a meeting, THE system SHALL name the file as `YYYY-MM-DD - Title.md` with special characters sanitized from the title.
- 5.3: IF a file with the same name already exists, THEN THE system SHALL append a numeric suffix (`(2)`, `(3)`, etc.) to avoid overwriting.
- 5.4: WHEN writing a file, THE system SHALL use atomic writes (temp file + rename) to prevent partial or corrupt files.

### 6. CLI Interface

**As a** user,
**I want** a consistent CLI with subcommands per connector,
**so that** I can manage each source independently.

**Acceptance Criteria:**

- 6.1: WHEN running `meeting-export`, THE system SHALL present two subcommand groups: `fathom` and `gmeet`.
- 6.2: WHEN running `meeting-export {connector} sync`, THE system SHALL support `--since`, `--until`, `--force`, `--dry-run`, and `--limit` flags.
- 6.3: WHEN running `meeting-export {connector} list`, THE system SHALL display available meetings with their export status.
- 6.4: WHEN running `meeting-export {connector} status`, THE system SHALL show the state file path, output directory, last sync time, and exported count.
- 6.5: WHEN running `meeting-export {connector} reset`, THE system SHALL prompt for confirmation before clearing the SyncState.
- 6.6: WHERE `--dry-run` is specified, THE system SHALL log what would be exported without writing any files or updating state.
- 6.7: WHERE `-v` / `--verbose` is specified at the top level, THE system SHALL enable debug-level logging.

### 7. Resilience and Rate Limiting

**As a** user syncing large backlogs,
**I want** the tool to handle API errors and rate limits gracefully,
**so that** syncs complete reliably without manual intervention.

**Acceptance Criteria:**

- 7.1: IF a Fathom API request fails with a 5xx error or transport error, THEN THE system SHALL retry up to 3 times with exponential backoff (2^attempt seconds).
- 7.2: IF a Fathom API request receives a 429 rate-limit response, THEN THE system SHALL wait for the duration specified in the `RateLimit-Reset` header before retrying.
- 7.3: WHILE the Fathom client is making requests, THE system SHALL enforce a sliding-window rate limit (configurable, default 50 requests/minute).
- 7.4: IF a Google Drive document export fails for a single event, THEN THE system SHALL log a warning and continue processing remaining events.

### 8. Configuration

**As a** user,
**I want** to configure the tool via environment variables and optional files,
**so that** credentials and preferences are kept outside version control.

**Acceptance Criteria:**

- 8.1: WHEN loading configuration, THE system SHALL read from a `.env` file in the project root and from environment variables.
- 8.2: WHEN the required `FATHOM_API_KEY` is missing for a Fathom command, THE system SHALL exit with a clear error message.
- 8.3: WHEN the Google OAuth `client_secret.json` is missing for a GMeet command, THE system SHALL exit with a clear error message indicating the expected path.
- 8.4: WHILE handling credentials, THE system SHALL never write API keys, OAuth secrets, or tokens to version-controlled files (enforced via `.gitignore`).
