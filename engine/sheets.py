"""Google Sheets lead capture via gspread + service account."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import gspread
from gspread import Spreadsheet, Worksheet

_client: Optional[gspread.Client] = None

LEAD_HEADERS = [
    "Timestamp", "Name", "Email", "Phone", "Province", "Timing",
    "Birth Type", "Care Complexity", "NOH Low", "NOH High",
    "FFS Low", "FFS High", "Source Page",
]


def _get_sheets_client() -> Optional[gspread.Client]:
    """Auth via GOOGLE_SHEETS_CREDENTIALS env var (service account JSON)."""
    global _client
    if _client is not None:
        return _client

    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
    if not creds_json:
        return None

    try:
        creds_dict = json.loads(creds_json)
        _client = gspread.service_account_from_dict(creds_dict)
        return _client
    except Exception:
        return None


def _get_worksheet(sheet_id: str) -> Optional[Worksheet]:
    """Open the 'Leads' worksheet (or first sheet) from the given spreadsheet."""
    client = _get_sheets_client()
    if not client:
        return None
    try:
        spreadsheet: Spreadsheet = client.open_by_key(sheet_id)
        try:
            return spreadsheet.worksheet("Leads")
        except gspread.exceptions.WorksheetNotFound:
            return spreadsheet.sheet1
    except Exception:
        return None


def append_lead(row_dict: Dict[str, str]) -> bool:
    """
    Append a lead row to the Google Sheet.

    row_dict keys should match LEAD_HEADERS. Missing keys get empty strings.
    Returns True on success, False on failure (non-blocking).
    """
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
    if not sheet_id:
        return False

    ws = _get_worksheet(sheet_id)
    if not ws:
        return False

    try:
        row_dict.setdefault("Timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        row = [str(row_dict.get(h, "")) for h in LEAD_HEADERS]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False
