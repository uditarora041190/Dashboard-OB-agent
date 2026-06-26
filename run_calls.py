"""
run_calls.py
------------
Reads leads from leads_enriched.csv (preferred) or leads.csv and triggers
outbound calls via Vapi, injecting per-lead research into the agent's context.

Usage:
    python run_calls.py                        # Call all leads
    python run_calls.py --limit 10             # Call only the first 10 leads
    python run_calls.py --dry-run              # Preview leads without making calls
    python run_calls.py --assistant-id <ID>    # Override stored assistant ID
    python run_calls.py --no-enriched          # Force use of leads.csv even if enriched exists

Recommended flow:
    python research_leads.py   # Research first
    python run_calls.py        # Then call with personalized context

CSV columns: name, phone, company (optional), notes (optional), website (optional)
"""

import csv
import json
import os
import sys
import time
import argparse
import datetime
import requests
from dotenv import load_dotenv

# Google Sheets logging (optional — gracefully skipped if not configured)
try:
    from sheets_logger import SheetsLogger
    _sheets_available = True
except ImportError:
    _sheets_available = False

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID")
VAPI_BASE_URL = "https://api.vapi.ai"
LEADS_FILE = "leads.csv"
ENRICHED_FILE = "leads_enriched.csv"
LOG_FILE = "call_log.csv"
ASSISTANT_ID_FILE = ".assistant_id"

# Seconds to wait between calls (respect rate limits & avoid spam)
CALL_DELAY_SECONDS = int(os.getenv("CALL_DELAY_SECONDS", "5"))


def load_assistant_id(override: str | None) -> str:
    if override:
        return override
    if os.path.exists(ASSISTANT_ID_FILE):
        with open(ASSISTANT_ID_FILE) as f:
            return f.read().strip()
    assistant_id = os.getenv("VAPI_ASSISTANT_ID", "")
    if assistant_id:
        return assistant_id
    print("ERROR: No assistant ID found.")
    print("  Run: python setup_assistant.py")
    print("  Or set VAPI_ASSISTANT_ID in your .env file.")
    sys.exit(1)


def load_leads(filepath: str) -> list[dict]:
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found. Copy leads_example.csv to leads.csv and fill it in.")
        sys.exit(1)
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        leads = []
        for i, row in enumerate(reader, start=2):  # row 1 is header
            phone = row.get("phone", "").strip()
            name = row.get("name", "").strip()
            if not phone:
                print(f"  WARNING: Row {i} missing phone number — skipping.")
                continue
            if not phone.startswith("+"):
                print(f"  WARNING: Row {i} phone '{phone}' should be in E.164 format (+1XXXXXXXXXX) — skipping.")
                continue
            leads.append({k: v for k, v in row.items()})
            leads[-1]["name"] = name or "there"
        return leads


def build_research_context(lead: dict) -> dict:
    """Build variable substitutions from enriched lead data for Vapi assistant overrides."""
    is_enriched = "pitch_angle" in lead

    if not is_enriched:
        return {
            "research_pitch_angle": "No pre-call research available — use standard discovery questions.",
            "research_website_url": lead.get("website", "unknown"),
            "research_website_live": "unknown",
            "research_running_meta_ads": "unknown",
            "research_running_google_ads": "unknown",
            "research_has_google_analytics": "unknown",
            "research_social_summary": "unknown",
            "research_site_issues": "none detected",
        }

    # Build social summary string
    social_parts = []
    for platform in ["facebook", "instagram", "linkedin", "twitter", "youtube", "tiktok"]:
        val = lead.get(f"social_{platform}", "")
        if val:
            social_parts.append(platform)
    social_summary = ", ".join(social_parts) if social_parts else "none found"

    # Build site issues string
    issues = []
    if lead.get("thin_site") in [True, "True", "true"]:
        issues.append("thin/sparse content")
    if lead.get("mobile_ready") in [False, "False", "false"]:
        issues.append("not mobile-friendly")
    if not lead.get("has_blog") or lead.get("has_blog") in ["False", "false"]:
        issues.append("no blog/content")
    site_issues = ", ".join(issues) if issues else "none detected"

    return {
        "research_pitch_angle": lead.get("pitch_angle", "Use standard discovery questions."),
        "research_website_url": lead.get("website_url") or lead.get("website") or "none found",
        "research_website_live": str(lead.get("website_live", "unknown")),
        "research_running_meta_ads": str(lead.get("running_meta_ads", "unknown")),
        "research_running_google_ads": str(lead.get("running_google_ads", "unknown")),
        "research_has_google_analytics": str(lead.get("has_google_analytics", "unknown")),
        "research_social_summary": social_summary,
        "research_site_issues": site_issues,
    }


def make_call(lead: dict, assistant_id: str, phone_number_id: str) -> dict:
    """POST /call — trigger a single outbound call."""
    research_vars = build_research_context(lead)

    variable_values = {
        "customer.name": lead.get("name", ""),
        "customer.company": lead.get("company", ""),
        **research_vars,
    }

    payload = {
        "assistantId": assistant_id,
        "phoneNumberId": phone_number_id,
        "customer": {
            "number": lead["phone"],
            "name": lead.get("name", ""),
        },
        "assistantOverrides": {
            "variableValues": variable_values,
        },
    }

    # Pass notes as a variable so the assistant can reference them
    if lead.get("notes"):
        payload["assistantOverrides"]["variableValues"]["research_extra_notes"] = lead["notes"]

    response = requests.post(
        f"{VAPI_BASE_URL}/call",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def get_call_status(call_id: str) -> dict:
    """GET /call/:id — fetch call details/status."""
    response = requests.get(
        f"{VAPI_BASE_URL}/call/{call_id}",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
    )
    response.raise_for_status()
    return response.json()


def init_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "name", "phone", "company",
                "call_id", "status", "error"
            ])


def log_call(lead: dict, call_id: str, status: str, error: str = ""):
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.datetime.now().isoformat(),
            lead["name"],
            lead["phone"],
            lead["company"],
            call_id,
            status,
            error,
        ])


def main():
    if not VAPI_API_KEY:
        print("ERROR: VAPI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Run outbound sales calls via Vapi.")
    parser.add_argument("--limit", type=int, help="Max number of leads to call.")
    parser.add_argument("--row", type=int, help="Call only this row number (1-indexed, e.g. --row 2).")
    parser.add_argument("--dry-run", action="store_true", help="Preview leads without calling.")
    parser.add_argument("--assistant-id", help="Override the stored assistant ID.")
    parser.add_argument("--no-enriched", action="store_true", help="Use leads.csv even if leads_enriched.csv exists.")
    args = parser.parse_args()

    assistant_id = load_assistant_id(args.assistant_id)
    phone_number_id = VAPI_PHONE_NUMBER_ID

    if not phone_number_id and not args.dry_run:
        print("ERROR: VAPI_PHONE_NUMBER_ID not set in .env.")
        print("  Add a phone number in the Vapi dashboard and paste its ID into .env.")
        sys.exit(1)

    # Prefer enriched leads (post research_leads.py) over raw leads
    use_enriched = not args.no_enriched and os.path.exists(ENRICHED_FILE)
    leads_path = ENRICHED_FILE if use_enriched else LEADS_FILE
    leads = load_leads(leads_path)

    if args.row:
        idx = args.row - 1
        if idx < 0 or idx >= len(leads):
            print(f"ERROR: --row {args.row} is out of range (file has {len(leads)} leads).")
            sys.exit(1)
        leads = [leads[idx]]
    elif args.limit:
        leads = leads[: args.limit]

    print(f"\nOutbound Sales Agent")
    print(f"{'='*40}")
    print(f"  Assistant ID : {assistant_id}")
    print(f"  Phone ID     : {phone_number_id or 'N/A (dry run)'}")
    print(f"  Leads file   : {leads_path}")
    print(f"  Enriched     : {'YES — personalized research active' if use_enriched else 'no — run research_leads.py first for best results'}")
    print(f"  Leads loaded : {len(leads)}")
    print(f"  Dry run      : {'YES' if args.dry_run else 'no'}")
    print(f"{'='*40}\n")

    if args.dry_run:
        print("Leads preview:")
        for i, lead in enumerate(leads, 1):
            print(f"  {i:3}. {lead['name']:<20} {lead['phone']:<16} {lead['company']}")
        print("\nDry run complete. Remove --dry-run to make real calls.")
        return

    init_log()
    success_count = 0
    fail_count = 0

    # Initialize Sheets logger once (if configured)
    sheets_logger = None
    if _sheets_available and os.getenv("GOOGLE_SHEET_ID"):
        try:
            sheets_logger = SheetsLogger()
            print("  [sheets] Google Sheets logging active")
        except Exception as e:
            print(f"  [sheets] Warning: could not connect to Sheets — {e}")

    for i, lead in enumerate(leads, 1):
        label = f"[{i}/{len(leads)}]"
        print(f"{label} Calling {lead['name']} ({lead['phone']})...", end=" ", flush=True)

        try:
            call = make_call(lead, assistant_id, phone_number_id)
            call_id = call.get("id", "unknown")
            print(f"OK  call_id={call_id}")
            log_call(lead, call_id, "queued")
            if sheets_logger:
                try:
                    sheets_logger.log_lead(lead, call_id)
                except Exception as e:
                    print(f"  [sheets] Warning: {e}")
            success_count += 1
        except requests.HTTPError as e:
            error_msg = str(e)
            try:
                error_msg = e.response.json().get("message", error_msg)
            except Exception:
                pass
            print(f"FAIL  {error_msg}")
            log_call(lead, "", "error", error_msg)
            fail_count += 1
        except Exception as e:
            print(f"FAIL  {e}")
            log_call(lead, "", "error", str(e))
            fail_count += 1

        if i < len(leads):
            time.sleep(CALL_DELAY_SECONDS)

    print(f"\n{'='*40}")
    print(f"  Done. Queued: {success_count}  Failed: {fail_count}")
    print(f"  Results logged to {LOG_FILE}")
    print(f"  View live call activity at: https://dashboard.vapi.ai/calls")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
