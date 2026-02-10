from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class GmailSettings(BaseModel):
    label_inbox: str = "TA/Admin"
    label_processed: str = "TA/Admin/Processed"


class DriveSettings(BaseModel):
    target_folder_name: str = "TA Admin 2026_Nelly"


class SheetsSettings(BaseModel):
    spreadsheet_id: str
    ledger_tab: str = "Ledger"
    todos_tab: str = "TODOs"


class ProcessingSettings(BaseModel):
    dry_run: bool = False
    max_messages: int = 50
    workdir: str = ".admin_automator_work"


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    allowlisted_senders: List[str] = Field(default_factory=list)
    gmail: GmailSettings = Field(default_factory=GmailSettings)
    drive: DriveSettings = Field(default_factory=DriveSettings)
    sheets: Optional[SheetsSettings] = None
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)


def default_config_path() -> Path:
    return Path("~/.config/admin-automator/config.yaml").expanduser()


def load_settings(path: Optional[Path] = None) -> Settings:
    path = path or default_config_path()
    if not path.exists():
        # allow running with env-only values
        return Settings()

    data = yaml.safe_load(path.read_text()) or {}
    return Settings.model_validate(data)
