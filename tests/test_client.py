import json
import re
from pathlib import Path

import httpx
import pytest

from meeting_export.fathom.client import FathomClient
from meeting_export.fathom.config import Config

FIXTURE = Path(__file__).parent / "fixtures" / "meeting_response.json"

MEETINGS_URL = re.compile(r"https://api\.fathom\.ai/external/v1/meetings(\?.*)?$")


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(api_key="test-key", state_file=tmp_path / "state.json")


def test_list_meetings_single_page(httpx_mock, config: Config):
    meeting = json.loads(FIXTURE.read_text())
    httpx_mock.add_response(
        url=MEETINGS_URL,
        json={"items": [meeting], "next_cursor": None},
    )

    with FathomClient(config) as client:
        results = list(client.list_meetings())

    assert len(results) == 1
    assert results[0]["recording_id"] == 98765


def test_list_meetings_pagination(httpx_mock, config: Config):
    meeting = json.loads(FIXTURE.read_text())
    httpx_mock.add_response(
        url=MEETINGS_URL,
        json={"items": [meeting], "next_cursor": "page2"},
    )
    meeting2 = dict(meeting, recording_id=11111, title="Second Meeting")
    httpx_mock.add_response(
        url=MEETINGS_URL,
        json={"items": [meeting2], "next_cursor": None},
    )

    with FathomClient(config) as client:
        results = list(client.list_meetings())

    assert len(results) == 2
    assert results[1]["recording_id"] == 11111


def test_get_transcript(httpx_mock, config: Config):
    httpx_mock.add_response(
        url="https://api.fathom.ai/external/v1/recordings/98765/transcript",
        json={"transcript": [{"speaker": {"display_name": "Alice"}, "text": "Hello", "timestamp": "00:00:01"}]},
    )

    with FathomClient(config) as client:
        transcript = client.get_transcript(98765)

    assert len(transcript) == 1
    assert transcript[0]["text"] == "Hello"


def test_auth_header(httpx_mock, config: Config):
    httpx_mock.add_response(json={"items": [], "next_cursor": None})

    with FathomClient(config) as client:
        list(client.list_meetings())

    request = httpx_mock.get_request()
    assert request.headers["X-Api-Key"] == "test-key"
