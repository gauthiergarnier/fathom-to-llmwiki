import json
from pathlib import Path

from meeting_export.fathom.converter import fathom_make_filename, meeting_to_markdown

FIXTURE = Path(__file__).parent / "fixtures" / "meeting_response.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_markdown_has_frontmatter():
    md = meeting_to_markdown(_load_fixture())
    assert md.startswith("---\n")
    assert '\ntitle: "Q2 Strategy Review"\n' in md
    assert "\ndate: 2026-05-10\n" in md
    assert "\ntype: fathom-transcript\n" in md
    assert "\nsource: fathom\n" in md
    assert "  - fathom-transcript\n" in md


def test_markdown_has_summary():
    md = meeting_to_markdown(_load_fixture())
    assert "## Summary" in md
    assert "platform migration targets" in md


def test_markdown_has_action_items():
    md = meeting_to_markdown(_load_fixture())
    assert "## Action Items" in md
    assert "- [ ] Send updated Acme CRM integration timeline (Alice Martin)" in md
    assert "- [ ] Draft Globex Q3 proposal outline (Bob Chen)" in md


def test_markdown_has_transcript():
    md = meeting_to_markdown(_load_fixture())
    assert "## Transcript" in md
    assert "**Jane Smith** (00:00:15)" in md
    assert "**Alice Martin** (00:00:32)" in md
    assert "API versioning issue" in md


def test_markdown_participants_in_frontmatter():
    md = meeting_to_markdown(_load_fixture())
    assert '"Alice Martin <alice@example.com>"' in md
    assert '"Bob Chen <bob@partner.com>"' in md


def test_markdown_duration():
    md = meeting_to_markdown(_load_fixture())
    assert "44 min" in md


def test_markdown_omits_summary_when_missing():
    meeting = _load_fixture()
    meeting["default_summary"] = None
    md = meeting_to_markdown(meeting)
    assert "## Summary" not in md
    assert "## Transcript" in md


def test_markdown_omits_action_items_when_empty():
    meeting = _load_fixture()
    meeting["action_items"] = []
    md = meeting_to_markdown(meeting)
    assert "## Action Items" not in md


def test_transcript_has_block_ids():
    md = meeting_to_markdown(_load_fixture())
    assert "^t-15\n" in md
    assert "^t-32\n" in md
    assert "^t-65\n" in md


def test_summary_fathom_links_rewritten():
    meeting = _load_fixture()
    meeting["default_summary"] = {
        "markdown_formatted": "[Key insight about budgets.](https://fathom.video/share/abc?tab=summary&timestamp=32.0)"
    }
    md = meeting_to_markdown(meeting)
    assert "fathom.video" not in md.split("## Summary")[1].split("## ")[0]
    assert "[Key insight about budgets.](#^t-32)" in md


def test_summary_links_find_closest_anchor():
    meeting = _load_fixture()
    meeting["default_summary"] = {
        "markdown_formatted": "[Some point.](https://fathom.video/share/x?timestamp=40.0)"
    }
    md = meeting_to_markdown(meeting)
    assert "[Some point.](#^t-32)" in md


def test_make_filename():
    meeting = _load_fixture()
    assert fathom_make_filename(meeting) == "2026-05-10 - Q2 Strategy Review.md"


def test_make_filename_sanitizes_special_chars():
    meeting = _load_fixture()
    meeting["title"] = 'Meeting: "Important" Q&A <draft>'
    name = fathom_make_filename(meeting)
    assert ":" not in name
    assert '"' not in name
    assert "<" not in name
    assert ">" not in name
    assert name.endswith(".md")


def test_make_filename_truncates_long_title():
    meeting = _load_fixture()
    meeting["title"] = "A" * 200
    name = fathom_make_filename(meeting)
    assert len(name) <= 120


def test_make_filename_untitled():
    meeting = _load_fixture()
    meeting["title"] = None
    name = fathom_make_filename(meeting)
    assert "Untitled Meeting" in name
