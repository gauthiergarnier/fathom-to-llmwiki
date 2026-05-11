from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str = "https://api.fathom.ai/external/v1"
    output_dir: Path = field(default_factory=lambda: Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "Knowlegde-Pro")
    output_subdir: str = "Fathom Transcripts"
    state_file: Path = field(default_factory=lambda: Path(".fathom-export-state.json"))
    rate_limit_per_minute: int = 50
    recorded_by: list[str] = field(default_factory=list)
    title_filter: list[str] = field(default_factory=list)
    title_exclude: list[str] = field(default_factory=list)

    @property
    def transcript_dir(self) -> Path:
        return self.output_dir / self.output_subdir

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        load_dotenv(env_file or Path(".env"))
        api_key = os.environ.get("FATHOM_API_KEY", "")
        if not api_key:
            raise ValueError("FATHOM_API_KEY is required — set it in .env or as an environment variable")

        kwargs: dict = {"api_key": api_key}
        if v := os.environ.get("FATHOM_BASE_URL"):
            kwargs["base_url"] = v
        if v := os.environ.get("OUTPUT_DIR"):
            kwargs["output_dir"] = Path(v)
        if v := os.environ.get("OUTPUT_SUBDIR"):
            kwargs["output_subdir"] = v
        if v := os.environ.get("STATE_FILE"):
            kwargs["state_file"] = Path(v)
        if v := os.environ.get("RATE_LIMIT_PER_MINUTE"):
            kwargs["rate_limit_per_minute"] = int(v)
        if v := os.environ.get("RECORDED_BY"):
            kwargs["recorded_by"] = [e.strip() for e in v.split(",") if e.strip()]
        if v := os.environ.get("TITLE_FILTER"):
            kwargs["title_filter"] = [t.strip() for t in v.split(",") if t.strip()]
        if v := os.environ.get("TITLE_EXCLUDE"):
            kwargs["title_exclude"] = [t.strip() for t in v.split(",") if t.strip()]

        return cls(**kwargs)
