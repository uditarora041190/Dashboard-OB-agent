"""
auth_google.py
--------------
One-time Google authentication setup.
Run this ONCE to connect your Google account.
It opens a browser, you log in, and saves a token.json for future use.

Usage:
    python3 auth_google.py

What it sets up:
    - Google Sheets access (to log calls and research)
    - Google Calendar access (to create Meet links for bookings)

After running, token.json is saved and all other scripts use it automatically.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
TOKEN_FILE = "token.json"


def authenticate():
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing Google token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"\nERROR: {CREDENTIALS_FILE} not found.")
                print("\nTo set this up:")
                print("  1. Go to https://console.cloud.google.com")
                print("  2. Create a project (or select existing)")
                print("  3. Enable: Google Sheets API + Google Calendar API")
                print("  4. Go to APIs & Services → Credentials")
                print("  5. Create credentials → OAuth 2.0 Client ID → Desktop App")
                print("  6. Download the JSON and save it as: google_credentials.json")
                print("  7. Run this script again\n")
                return None

            print("Opening browser for Google login...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"  Token saved to {TOKEN_FILE}")

    return creds


def verify_access(creds):
    """Verify Sheets and Calendar access actually works."""
    print("\nVerifying Google Sheets access...")
    try:
        import gspread
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if sheet_id:
            spreadsheet = client.open_by_key(sheet_id)
            print(f"  ✓ Sheet access confirmed: '{spreadsheet.title}'")
        else:
            print("  ✓ Sheets auth OK (GOOGLE_SHEET_ID not set yet — add it to .env)")
    except Exception as e:
        print(f"  ✗ Sheets error: {e}")

    print("Verifying Google Calendar access...")
    try:
        service = build("calendar", "v3", credentials=creds)
        calendars = service.calendarList().list().execute()
        primary = next(
            (c for c in calendars.get("items", []) if c.get("primary")), None
        )
        if primary:
            print(f"  ✓ Calendar access confirmed: {primary.get('summary')}")
        else:
            print("  ✓ Calendar auth OK")
    except Exception as e:
        print(f"  ✗ Calendar error: {e}")


def main():
    print("\nGoogle Authentication Setup")
    print("=" * 40)
    creds = authenticate()
    if creds:
        verify_access(creds)
        print("\n✓ All done! You're connected to Google.")
        print("  token.json saved — other scripts will use it automatically.")
        print("\nNext step: make sure GOOGLE_SHEET_ID is in your .env file.")
        print("  Create a Google Sheet, copy the ID from the URL:")
        print("  https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit")
        print("  Add to .env: GOOGLE_SHEET_ID=THIS_PART_HERE\n")


if __name__ == "__main__":
    main()
