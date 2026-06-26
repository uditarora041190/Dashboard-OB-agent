"""
sync_leads_to_sheet.py
----------------------
One-time script to push all leads from leads_enriched.csv into Google Sheet.
Useful for populating the sheet without making calls.

Usage:
    python3 sync_leads_to_sheet.py
"""

import csv
import os
from dotenv import load_dotenv
from sheets_logger import SheetsLogger

load_dotenv()

ENRICHED_FILE = "leads_enriched.csv"

def main():
    if not os.path.exists(ENRICHED_FILE):
        print(f"ERROR: {ENRICHED_FILE} not found. Run research_leads.py first.")
        return

    with open(ENRICHED_FILE, newline="", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))

    if not leads:
        print("No leads found in file.")
        return

    print(f"Connecting to Google Sheets...")
    logger = SheetsLogger()
    print(f"Connected. Syncing {len(leads)} leads...\n")

    for i, lead in enumerate(leads, 1):
        name = lead.get("name", "unknown")
        company = lead.get("company", "")
        phone = lead.get("phone", "")
        fake_call_id = f"manual-sync-{i}-{phone}"
        try:
            logger.log_lead(lead, fake_call_id)
            print(f"  [{i}] ✓ {name} — {company}")
        except Exception as e:
            print(f"  [{i}] ✗ {name} — ERROR: {e}")

    print(f"\nDone. Check your Google Sheet.")

if __name__ == "__main__":
    main()
