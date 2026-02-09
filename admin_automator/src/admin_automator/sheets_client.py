from __future__ import annotations

from datetime import datetime
from typing import Any

from googleapiclient.discovery import Resource


def append_row(
    service: Resource,
    *,
    spreadsheet_id: str,
    tab_name: str,
    values: list[Any],
) -> None:
    range_ = f"{tab_name}!A1"
    body = {"values": [values]}
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def upsert_todo(
    service: Resource,
    *,
    spreadsheet_id: str,
    tab_name: str,
    message_id: str,
    summary: str,
    details: str,
) -> None:
    # Simple strategy: append a TODO row; dedupe can be added later.
    now = datetime.now().isoformat(timespec="seconds")
    append_row(
        service,
        spreadsheet_id=spreadsheet_id,
        tab_name=tab_name,
        values=[now, message_id, summary, details],
    )
