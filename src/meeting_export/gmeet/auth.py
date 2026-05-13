from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from .config import Config

log = logging.getLogger(__name__)


def get_credentials(config: Config) -> Credentials:
    creds: Credentials | None = None

    if config.token_path.exists():
        creds = Credentials.from_authorized_user_file(str(config.token_path), config.scopes)

    if creds and creds.expired and creds.refresh_token:
        log.info("Refreshing expired token...")
        creds.refresh(Request())
        _save_token(creds, config.token_path)
    elif not creds or not creds.valid:
        if not config.client_secret_path.exists():
            raise FileNotFoundError(
                f"OAuth client secret not found at {config.client_secret_path}\n"
                "Download it from Google Cloud Console → APIs & Services → Credentials"
            )
        log.info("Starting OAuth flow (opening browser)...")
        flow = InstalledAppFlow.from_client_secrets_file(str(config.client_secret_path), config.scopes)
        creds = flow.run_local_server(port=0)
        _save_token(creds, config.token_path)

    return creds


def build_calendar_service(creds: Credentials) -> Resource:
    return build("calendar", "v3", credentials=creds)


def build_drive_service(creds: Credentials) -> Resource:
    return build("drive", "v3", credentials=creds)


def _save_token(creds: Credentials, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json(), encoding="utf-8")
    log.info("Token saved to %s", path)
