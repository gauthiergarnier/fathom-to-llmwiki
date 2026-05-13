from pathlib import Path

from meeting_export.shared.state import SyncState


def test_fresh_state(tmp_path: Path):
    state = SyncState(tmp_path / "state.json")
    assert state.exported_count == 0
    assert state.last_sync_at is None
    assert not state.is_exported(123)


def test_mark_and_check(tmp_path: Path):
    path = tmp_path / "state.json"
    state = SyncState(path)
    state.mark_exported(123, "Test Meeting", "Fathom Transcripts/2026-05-10 - Test Meeting.md")
    state.save()

    assert state.is_exported(123)
    assert state.is_exported("123")
    assert state.exported_count == 1
    assert state.last_sync_at is not None


def test_persistence(tmp_path: Path):
    path = tmp_path / "state.json"
    state = SyncState(path)
    state.mark_exported(456, "Persisted", "path.md")
    state.save()

    state2 = SyncState(path)
    assert state2.is_exported(456)
    assert state2.exported_count == 1


def test_reset(tmp_path: Path):
    path = tmp_path / "state.json"
    state = SyncState(path)
    state.mark_exported(789, "To Reset", "path.md")
    state.save()
    assert path.exists()

    state.reset()
    assert not path.exists()
    assert state.exported_count == 0


def test_corrupt_state_file(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("not valid json!!!")
    state = SyncState(path)
    assert state.exported_count == 0
