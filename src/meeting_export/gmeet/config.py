from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    client_secret_path: Path = field(default_factory=lambda: Path("credentials/client_secret.json"))
    token_path: Path = field(default_factory=lambda: Path.home() / ".gmeet-to-llmwiki" / "token.json")
    output_dir: Path = field(default_factory=lambda: Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "Knowlegde-Pro")
    output_subdir: str = "Google Meet Transcripts"
    state_file: Path = field(default_factory=lambda: Path(".gmeet-export-state.json"))

    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ])

    @property
    def transcript_dir(self) -> Path:
        return self.output_dir / self.output_subdir

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        load_dotenv(env_file or Path(".env"))

        kwargs: dict = {}
        if v := os.environ.get("GOOGLE_CLIENT_SECRET"):
            kwargs["client_secret_path"] = Path(v).expanduser()
        if v := os.environ.get("GOOGLE_TOKEN_PATH"):
            kwargs["token_path"] = Path(v).expanduser()
        if v := os.environ.get("OUTPUT_DIR"):
            kwargs["output_dir"] = Path(v).expanduser()
        if v := os.environ.get("GMEET_OUTPUT_SUBDIR"):
            kwargs["output_subdir"] = v
        if v := os.environ.get("GMEET_STATE_FILE"):
            kwargs["state_file"] = Path(v)

        return cls(**kwargs)
