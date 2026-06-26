"""
sheets_logger.py
----------------
Handles all Google Sheets logging for the outbound sales agent.

Sheet columns:
  Lead Info       : Timestamp, Name, Phone, Company, Website, SEO Score, SEO Grade,
                    SEO Issues, Meta Ads, Google Ads, Social Presence, Pitch Angle
  Call Info       : Call ID, Call Status, Call Time, Duration (s), Outcome,
                    Interested, Pain Point
  Transcript      : Full Transcript, Call Summary
  Booking         : Meeting Time, Google Meet Link

Usage (imported by run_calls.py and webhook_server.py):
    from sheets_logger import SheetsLogger
    logger = SheetsLogger()
    row_num = logger.log_lead(lead, call_id)
    logger.update_call_result(call_id, call_data)
    logger.update_booking(call_id, meeting_time, meet_link)
"""

import os
import json
import datetime
import gspread
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
TOKEN_FILE = "token.json"
SHEET_NAME = "Sales Calls"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    # Lead research
    "Timestamp", "Name", "Phone", "Company", "Website",
    "SEO Score", "SEO Grade", "SEO Issues",
    "Meta Ads", "Google Ads", "Social Presence",
    "Pitch Angle",
    # Call
    "Call ID", "Call Status", "Call Time", "Duration (s)",
    "Outcome", "Interested", "Pain Point",
    # Transcript
    "Call Summary", "Full Transcript",
    # Booking
    "Meeting Time", "Google Meet Link",
]


def _get_client() -> gspread.Client:
    """Authenticate and return a gspread client."""
    # Try service account first
    if os.path.exists(CREDENTIALS_FILE):
        creds_data = json.load(open(CREDENTIALS_FILE))
        if creds_data.get("type") == "service_account":
            creds = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=SCOPES
            )
            return gspread.authorize(creds)

    # Fall back to OAuth token (created by auth_google.py)
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return gspread.authorize(creds)

    raise RuntimeError(
        "No Google credentials found.\n"
        "Run: python3 auth_google.py\n"
        "Or place a service account JSON at: " + CREDENTIALS_FILE
    )


class SheetsLogger:
    def __init__(self):
        self.client = _get_client()
        self.sheet = self._get_or_create_sheet()

    def _get_or_create_sheet(self) -> gspread.Worksheet:
        """Open the spreadsheet and get/create the Sales Calls worksheet."""
        if not SHEET_ID:
            raise RuntimeError(
                "GOOGLE_SHEET_ID not set in .env.\n"
                "Create a Google Sheet, copy its ID from the URL, and add it to .env."
            )
        spreadsheet = self.client.open_by_key(SHEET_ID)
        try:
            ws = spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS)
            # Format header row
            ws.format("A1:W1", {
                "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            })
        # Ensure headers exist if sheet is empty
        existing = ws.row_values(1)
        if not existing:
            ws.append_row(HEADERS)
        return ws

    def _find_row_by_call_id(self, call_id: str) -> int | None:
        """Find the row number (1-indexed) for a given call ID."""
        try:
            col_index = HEADERS.index("Call ID") + 1
            col_values = self.sheet.col_values(col_index)
            for i, val in enumerate(col_values):
                if val == call_id:
                    return i + 1  # 1-indexed
        except Exception:
            pass
        return None

    def log_lead(self, lead: dict, call_id: str) -> int:
        """
        Append a new row for a lead when a call is queued.
        Returns the row number so it can be updated later.
        """
        social_parts = []
        for platform in ["facebook", "instagram", "linkedin", "twitter", "youtube", "tiktok"]:
            if lead.get(f"social_{platform}"):
                social_parts.append(platform)

        pitch = lead.get("pitch_angle", "")
        # Truncate pitch for sheet readability — full version stays in the briefing
        pitch_short = pitch[:500] + "..." if len(pitch) > 500 else pitch

        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            lead.get("name", ""),
            lead.get("phone", ""),
            lead.get("company", ""),
            lead.get("website_url") or lead.get("website", ""),
            lead.get("seo_score", ""),
            lead.get("seo_grade", ""),
            lead.get("seo_issues", "")[:300] if lead.get("seo_issues") else "",
            "Yes" if lead.get("running_meta_ads") in [True, "True"] else "No",
            "Yes" if lead.get("running_google_ads") in [True, "True"] else "No",
            ", ".join(social_parts) if social_parts else "None",
            pitch_short,
            call_id,
            "queued",
            "",   # Call Time (filled by webhook)
            "",   # Duration
            "",   # Outcome
            "",   # Interested
            "",   # Pain Point
            "",   # Call Summary
            "",   # Full Transcript
            "",   # Meeting Time
            "",   # Meet Link
        ]
        self.sheet.append_row(row, value_input_option="USER_ENTERED")
        # Return the row number of what we just appended
        return len(self.sheet.col_values(1))

    def update_call_result(self, call_id: str, call_data: dict):
        """
        Update a row with call results after the call ends.
        call_data keys: status, started_at, ended_at, duration,
                        outcome, interested, pain_point, summary, transcript
        """
        row_num = self._find_row_by_call_id(call_id)
        if not row_num:
            print(f"[sheets] WARNING: call_id {call_id} not found in sheet — appending new row")
            # Append minimal row if somehow missing
            self.sheet.append_row([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                call_data.get("customer_name", ""),
                call_data.get("customer_number", ""),
                "", "", "", "", "", "", "", "", "",
                call_id,
            ])
            row_num = len(self.sheet.col_values(1))

        def col(header: str) -> int:
            return HEADERS.index(header) + 1

        updates = {
            "Call Status": call_data.get("status", "ended"),
            "Call Time": call_data.get("started_at", ""),
            "Duration (s)": str(call_data.get("duration", "")),
            "Outcome": call_data.get("outcome", ""),
            "Interested": "Yes" if call_data.get("interested") else "No",
            "Pain Point": call_data.get("pain_point", ""),
            "Call Summary": call_data.get("summary", ""),
            "Full Transcript": call_data.get("transcript", "")[:50000],  # Sheets cell limit
        }

        for header, value in updates.items():
            self.sheet.update_cell(row_num, col(header), value or "")

        print(f"[sheets] Updated row {row_num} for call {call_id} → outcome: {call_data.get('outcome')}")

    def update_booking(self, call_id: str, meeting_time: str, meet_link: str, event_id: str = ""):
        """Update the booking columns for a call that resulted in a booked meeting."""
        row_num = self._find_row_by_call_id(call_id)
        if not row_num:
            print(f"[sheets] WARNING: call_id {call_id} not found — cannot update booking")
            return

        def col(header: str) -> int:
            return HEADERS.index(header) + 1

        self.sheet.update_cell(row_num, col("Meeting Time"), meeting_time)
        self.sheet.update_cell(row_num, col("Google Meet Link"), meet_link)
        # Highlight booked rows in green
        col_range = f"A{row_num}:W{row_num}"
        self.sheet.format(col_range, {
            "backgroundColor": {"red": 0.85, "green": 0.93, "blue": 0.83}
        })
        print(f"[sheets] Booking logged → row {row_num} | Meet: {meet_link}")
