# Tasks: Meeting Export

## 1. Shared Infrastructure

- [x] 1.1 Create `shared/state.py` with `SyncState` class (JSON persistence, mark/check exported, reset)
  _Requirements: 2.1, 2.2, 2.3_
- [x] 1.2 Create `shared/io.py` with `atomic_write`, `resolve_collision`, `sanitize_filename`
  _Requirements: 5.3, 5.4_
- [x] 1.3 Create `shared/convert.py` with `parse_dt`, `compute_duration`, `format_participants`, `make_filename`, `yaml_escape`
  _Requirements: 5.1, 5.2_
- [x] 1.4 **Checkpoint**: Unit tests for SyncState pass (fresh init, mark/check, persistence, reset, corrupt recovery)
  _Requirements: 2.1, 2.2, 2.3_

## 2. Fathom Connector

- [x] 2.1 Create `fathom/config.py` with `Config` dataclass and `from_env()` loader
  _Requirements: 8.1, 8.2_
- [x] 2.2 Create `fathom/client.py` with `FathomClient` (httpx, pagination, rate limiting, retry)
  _Requirements: 7.1, 7.2, 7.3_
- [x] 2.3 Create `fathom/profile.py` with TOML-based participant and title filtering
  _Requirements: 3.5_
- [x] 2.4 **Checkpoint**: Unit tests for FathomClient pass (pagination, auth, retry)
  _Requirements: 7.1, 7.2_
- [x] 2.5 Create `fathom/converter.py` with `meeting_to_markdown` (frontmatter, summary link rewriting, action items, transcript with block anchors)
  _Requirements: 3.2, 3.3, 3.4, 5.1_
- [x] 2.6 **Checkpoint**: Unit tests for converter pass (frontmatter, sections, link rewriting, filename sanitization)
  _Requirements: 3.2, 3.3, 3.4_
- [x] 2.7 Create `fathom/sync.py` with `run_sync` orchestration (list → filter → fetch → convert → write → state update)
  _Requirements: 1.1, 2.1, 2.4, 3.5, 3.6_
- [x] 2.8 Add batch mode support (`--batch N` loops until no new meetings)
  _Requirements: 3.7_

## 3. Google Meet Connector

- [x] 3.1 Create `gmeet/config.py` with `Config` dataclass and `from_env()` loader
  _Requirements: 8.1, 8.3_
- [x] 3.2 Create `gmeet/auth.py` with OAuth 2.0 Desktop App flow, token persistence, service builders
  _Requirements: 4.1_
- [x] 3.3 Create `gmeet/calendar_client.py` with `list_meet_events` (Calendar API, pagination, conference data filter)
  _Requirements: 4.2_
- [x] 3.4 Extract event attachments (`notes_attachment`, `recording_attachment`) from calendar event data
  _Requirements: 4.3_
- [x] 3.5 Create `gmeet/drive_client.py` with `export_doc_text` for Google Doc export by file ID
  _Requirements: 4.3_
- [x] 3.6 Create `gmeet/matcher.py` with attachment-based matching (use `fileId` from event attachments, not Drive title search)
  _Requirements: 4.3, 4.7_
- [x] 3.7 Implement Gemini notes detection (attachment title contains "Gemini") and cleaning (strip header, feedback UI, render sections)
  _Requirements: 4.4_
- [x] 3.8 Implement manual notes handling: extract date-headed section matching event date, skip if section is empty
  _Requirements: 4.5, 4.6_
- [x] 3.9 Handle `\r\n` line endings from Google Drive text export
  _Requirements: 4.4, 4.5_
- [x] 3.10 Create `gmeet/converter.py` with `meeting_to_markdown` (YAML frontmatter, Gemini mode, manual notes mode)
  _Requirements: 5.1, 4.4, 4.5_
- [x] 3.11 Create `gmeet/sync.py` with `run_sync` orchestration (calendar → match → convert → write → state update)
  _Requirements: 1.2, 2.1_
- [x] 3.12 **Checkpoint**: End-to-end test with `meeting-export gmeet sync --dry-run --limit 1` produces correct output
  _Requirements: 4.3, 4.4, 6.6_

## 4. CLI Layer

- [x] 4.1 Create `cli.py` with top-level Click group and `--verbose` flag
  _Requirements: 6.1, 6.7_
- [x] 4.2 Add `fathom` subgroup with commands: sync, list, export, status, reset
  _Requirements: 6.2, 6.3, 6.4, 6.5_
- [x] 4.3 Add `gmeet` subgroup with commands: auth, sync, list, status, reset
  _Requirements: 6.2, 6.3, 6.4, 6.5_
- [x] 4.4 Wire `--since`, `--until`, `--force`, `--dry-run`, `--limit` flags to sync functions
  _Requirements: 6.2, 6.6_
- [x] 4.5 **Checkpoint**: `meeting-export --help` shows both subgroups; `meeting-export fathom status` and `meeting-export gmeet status` work
  _Requirements: 6.1, 6.4_

## 5. Configuration and Packaging

- [x] 5.1 Configure `pyproject.toml` with entry point `meeting-export = "meeting_export.cli:main"` and all dependencies
  _Requirements: 8.1_
- [x] 5.2 Create `.env.example` with all Fathom and GMeet configuration variables
  _Requirements: 8.1_
- [x] 5.3 Configure `.gitignore` to exclude `.env`, state files, `credentials/client_secret.json`, token files
  _Requirements: 8.4_
- [x] 5.4 Create example profile files (`profiles/team.example.toml`, `profiles/customers.example.toml`)
  _Requirements: 3.5_
- [x] 5.5 **Checkpoint**: All existing tests pass with updated imports (`pytest`)
  _Requirements: all_

## 6. Pending

- [ ] 6.1 Add unit tests for GMeet converter (Gemini notes cleaning, manual notes section extraction)
  _Requirements: 4.4, 4.5, 4.6_
- [ ] 6.2 Add unit tests for GMeet matcher (attachment-based matching, empty section detection)
  _Requirements: 4.3, 4.6, 4.7_
- [ ] 6.3 Add unit tests for GMeet calendar_client (event extraction, attachment parsing)
  _Requirements: 4.2, 4.3_
- [ ] 6.4 Write `docs/specs/meeting-export/` specification documents (requirements, design, tasks)
  _Requirements: documentation_
