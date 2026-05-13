from pathlib import Path

from meeting_export.fathom.profile import Profile


def _write_profile(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "profile.toml"
    p.write_text(content)
    return p


def test_load_profile(tmp_path: Path):
    p = _write_profile(tmp_path, '''
[participants]
include = ["*@acme.com", "bob@partner.com"]
exclude = ["noreply@acme.com"]

[title]
include = ["Strategy"]
exclude = ["1:1"]
''')
    profile = Profile.load(p)
    assert profile.participant_include == ["*@acme.com", "bob@partner.com"]
    assert profile.participant_exclude == ["noreply@acme.com"]
    assert profile.title_include == ["Strategy"]
    assert profile.title_exclude == ["1:1"]


def test_domain_wildcard_match():
    profile = Profile(participant_include=["*@acme.com"])
    meeting = {
        "title": "Weekly",
        "calendar_invitees": [
            {"name": "Alice", "email": "alice@acme.com"},
        ],
    }
    assert profile.matches_meeting(meeting)


def test_domain_wildcard_no_match():
    profile = Profile(participant_include=["*@acme.com"])
    meeting = {
        "title": "Weekly",
        "calendar_invitees": [
            {"name": "Bob", "email": "bob@other.com"},
        ],
    }
    assert not profile.matches_meeting(meeting)


def test_exact_email_match():
    profile = Profile(participant_include=["bob@partner.com"])
    meeting = {
        "title": "Call",
        "calendar_invitees": [
            {"name": "Bob", "email": "bob@partner.com"},
        ],
    }
    assert profile.matches_meeting(meeting)


def test_participant_exclude():
    profile = Profile(
        participant_include=["*@acme.com"],
        participant_exclude=["noreply@acme.com"],
    )
    meeting = {
        "title": "Notification",
        "calendar_invitees": [
            {"name": "No Reply", "email": "noreply@acme.com"},
        ],
    }
    assert not profile.matches_meeting(meeting)


def test_participant_exclude_partial():
    profile = Profile(
        participant_include=["*@acme.com"],
        participant_exclude=["noreply@acme.com"],
    )
    meeting = {
        "title": "Weekly",
        "calendar_invitees": [
            {"name": "No Reply", "email": "noreply@acme.com"},
            {"name": "Alice", "email": "alice@acme.com"},
        ],
    }
    assert profile.matches_meeting(meeting)


def test_title_filter():
    profile = Profile(title_include=["Strategy"])
    assert profile.matches_meeting({"title": "Q2 Strategy Review", "calendar_invitees": []})
    assert not profile.matches_meeting({"title": "Weekly Standup", "calendar_invitees": []})


def test_title_exclude():
    profile = Profile(title_exclude=["Interview"])
    assert profile.matches_meeting({"title": "Strategy Call", "calendar_invitees": []})
    assert not profile.matches_meeting({"title": "Interview with Bob", "calendar_invitees": []})


def test_combined_title_and_participant():
    profile = Profile(
        participant_include=["*@acme.com"],
        title_exclude=["1:1"],
    )
    meeting_match = {
        "title": "Team Strategy",
        "calendar_invitees": [{"name": "A", "email": "a@acme.com"}],
    }
    meeting_excluded = {
        "title": "1:1 with Alice",
        "calendar_invitees": [{"name": "A", "email": "a@acme.com"}],
    }
    assert profile.matches_meeting(meeting_match)
    assert not profile.matches_meeting(meeting_excluded)


def test_no_filters_matches_all():
    profile = Profile()
    assert profile.matches_meeting({"title": "Anything", "calendar_invitees": []})


def test_api_domains_pure_wildcards():
    profile = Profile(participant_include=["*@acme.com", "*@partner.com"])
    assert profile.api_domains == ["acme.com", "partner.com"]


def test_api_domains_mixed_patterns():
    profile = Profile(participant_include=["*@acme.com", "bob@other.com"])
    assert profile.api_domains is None


def test_name_substring_match():
    profile = Profile(participant_include=["Alice"])
    meeting = {
        "title": "Call",
        "calendar_invitees": [{"name": "Alice Martin", "email": "alice@example.com"}],
    }
    assert profile.matches_meeting(meeting)
