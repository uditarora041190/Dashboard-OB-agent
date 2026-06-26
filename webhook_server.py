"""
webhook_server.py
-----------------
Flask server that receives Vapi call events and:
  1. Updates Google Sheet with call outcome, transcript, and summary
  2. Creates a Google Calendar event with Meet link if a call was booked
  3. Updates the sheet row with the Meet link

Vapi sends a POST to this server when each call ends.

Usage:
    python3 webhook_server.py

Then expose it publicly using ngrok:
    ngrok http 5055

Copy the ngrok URL (e.g. https://abc123.ngrok.io) and set it in Vapi:
    Dashboard → Assistants → Your Assistant → Server URL
    Set to: https://abc123.ngrok.io/vapi-webhook

Keep both this server and ngrok running while calls are active.
"""

import os
import json
import datetime
import re
from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from sheets_logger import SheetsLogger

load_dotenv()

app = Flask(__name__)

TOKEN_FILE = "token.json"
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")  # Optional: set in Vapi dashboard


# ── Google Calendar helpers ───────────────────────────────────────────────────

def get_calendar_service():
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("token.json not found. Run: python3 auth_google.py")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build("calendar", "v3", credentials=creds)


def create_meet_event(
    prospect_name: str,
    prospect_phone: str,
    meeting_time_str: str,
    duration_minutes: int = 15,
    notes: str = "",
) -> tuple[str, str]:
    """
    Create a Google Calendar event with a Meet link.
    Returns (meet_link, event_id).
    meeting_time_str: ISO format or natural language like "Thursday 3pm"
    """
    service = get_calendar_service()

    # Parse meeting time
    start_dt = _parse_meeting_time(meeting_time_str)
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

    event_body = {
        "summary": f"Discovery Call — {prospect_name}",
        "description": (
            f"Prospect: {prospect_name}\n"
            f"Phone: {prospect_phone}\n"
            f"Booked via AI sales agent\n\n"
            f"Notes:\n{notes}"
        ),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": os.getenv("TIMEZONE", "America/New_York"),
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": os.getenv("TIMEZONE", "America/New_York"),
        },
        "conferenceData": {
            "createRequest": {
                "requestId": f"sales-{prospect_phone}-{int(start_dt.timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},
                {"method": "popup", "minutes": 15},
            ],
        },
    }

    event = service.events().insert(
        calendarId="primary",
        body=event_body,
        conferenceDataVersion=1,
        sendUpdates="none",
    ).execute()

    meet_link = event.get("hangoutLink", "")
    event_id = event.get("id", "")
    return meet_link, event_id


def _parse_meeting_time(time_str: str) -> datetime.datetime:
    """
    Best-effort parse of a meeting time string from the call transcript.
    Falls back to next business day at 10am if parsing fails.
    """
    if not time_str:
        return _next_business_day_at(10)

    time_str = time_str.strip().lower()

    # Try ISO format first
    try:
        return datetime.datetime.fromisoformat(time_str)
    except Exception:
        pass

    # Day of week patterns: "thursday at 3pm", "friday 2:30pm"
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}
    for day_name, day_num in days.items():
        if day_name in time_str:
            hour, minute = _extract_time(time_str)
            return _next_weekday(day_num, hour, minute)

    # "tomorrow at Xpm"
    if "tomorrow" in time_str:
        hour, minute = _extract_time(time_str)
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return _next_business_day_at(10)


def _extract_time(text: str) -> tuple[int, int]:
    """Extract hour and minute from strings like '3pm', '2:30pm', '14:00'."""
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        period = match.group(3)
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return hour, minute
    return 10, 0


def _next_weekday(target_weekday: int, hour: int, minute: int) -> datetime.datetime:
    now = datetime.datetime.now()
    days_ahead = target_weekday - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target = now + datetime.timedelta(days=days_ahead)
    return target.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _next_business_day_at(hour: int) -> datetime.datetime:
    now = datetime.datetime.now()
    delta = 1
    while True:
        candidate = now + datetime.timedelta(days=delta)
        if candidate.weekday() < 5:  # Mon-Fri
            return candidate.replace(hour=hour, minute=0, second=0, microsecond=0)
        delta += 1


# ── Transcript cleanup ────────────────────────────────────────────────────────

def clean_transcript(text: str) -> str:
    """
    Fix common speech-to-text artifacts in transcripts:
    - "udit at brew labs media dot com" → "udit@brewlabsmedia.com"
    - "someone at domain dot com" → "someone@domain.com"
    - "www dot example dot com" → "www.example.com"
    """
    if not text:
        return text

    import re

    # Fix email addresses: "word at word dot word" → "word@word.word"
    # Handles multi-word domains like "brew labs media dot com" → "brewlabsmedia.com"
    def fix_email(m):
        user = m.group(1).strip()
        domain_raw = m.group(2).strip()
        # Remove spaces within domain parts (e.g. "brew labs media" → "brewlabsmedia")
        # Split on " dot " to get domain segments
        parts = re.split(r'\s+dot\s+', domain_raw, flags=re.IGNORECASE)
        # Remove spaces within each part
        parts = [''.join(p.split()) for p in parts]
        domain = '.'.join(parts)
        return f"{user}@{domain}"

    text = re.sub(
        r'(\w[\w.\-]*)\s+at\s+([\w\s]+(?:\s+dot\s+[\w\s]+)+)',
        fix_email,
        text,
        flags=re.IGNORECASE
    )

    # Fix standalone URLs: "www dot example dot com" → "www.example.com"
    def fix_url(m):
        parts = re.split(r'\s+dot\s+', m.group(0), flags=re.IGNORECASE)
        return '.'.join(''.join(p.split()) for p in parts)

    text = re.sub(
        r'www(?:\s+dot\s+\w+)+',
        fix_url,
        text,
        flags=re.IGNORECASE
    )

    return text


# ── Vapi webhook handler ──────────────────────────────────────────────────────

@app.route("/vapi-webhook", methods=["POST"])
def vapi_webhook():
    data = request.get_json(silent=True) or {}
    message = data.get("message", {})
    msg_type = message.get("type", "")

    # Only process end-of-call reports
    if msg_type != "end-of-call-report":
        return jsonify({"status": "ignored", "type": msg_type}), 200

    call = message.get("call", {})
    call_id = call.get("id", "")
    analysis = message.get("analysis", {}) or call.get("analysis", {}) or {}
    structured = analysis.get("structuredData", {}) or {}

    # Extract call details
    started_at = call.get("startedAt", "")
    ended_at = call.get("endedAt", "")
    duration = _calc_duration(started_at, ended_at)

    call_data = {
        "status": "completed",
        "started_at": started_at,
        "ended_at": ended_at,
        "duration": duration,
        "transcript": clean_transcript(message.get("transcript", "") or call.get("transcript", "")),
        "summary": clean_transcript(analysis.get("summary", "") or message.get("summary", "")),
        "outcome": structured.get("outcome", "unknown"),
        "interested": structured.get("interested", False),
        "pain_point": structured.get("pain_point", ""),
        "customer_name": call.get("customer", {}).get("name", ""),
        "customer_number": call.get("customer", {}).get("number", ""),
    }

    print(f"\n[webhook] Call ended: {call_id}")
    print(f"  Outcome  : {call_data['outcome']}")
    print(f"  Interested: {call_data['interested']}")
    print(f"  Duration : {duration}s")

    # Update sheet
    try:
        logger = SheetsLogger()
        logger.update_call_result(call_id, call_data)
    except Exception as e:
        print(f"[webhook] Sheet update error: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500

    # If booked — create Google Meet event
    if call_data["outcome"] == "booked_call":
        callback_time = structured.get("callback_time", "")
        print(f"  → Booking detected! Meeting time: '{callback_time}'")
        try:
            meet_link, event_id = create_meet_event(
                prospect_name=call_data["customer_name"],
                prospect_phone=call_data["customer_number"],
                meeting_time_str=callback_time,
                notes=call_data["summary"],
            )
            print(f"  → Meet link created: {meet_link}")
            logger.update_booking(call_id, callback_time, meet_link, event_id)
        except Exception as e:
            print(f"[webhook] Calendar error: {e}")
            # Don't fail the webhook — sheet is already updated
            logger.update_booking(call_id, callback_time, f"Calendar error: {e}")

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "server": "vapi-webhook"}), 200


def _calc_duration(started_at: str, ended_at: str) -> int:
    """Calculate call duration in seconds from ISO timestamps."""
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        start = datetime.datetime.strptime(started_at, fmt)
        end = datetime.datetime.strptime(ended_at, fmt)
        return int((end - start).total_seconds())
    except Exception:
        return 0


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", 5055))
    print(f"\nVapi Webhook Server")
    print(f"{'='*40}")
    print(f"  Listening on : http://localhost:{port}/vapi-webhook")
    print(f"  Health check : http://localhost:{port}/health")
    print(f"\n  To expose publicly, run in another terminal:")
    print(f"  ngrok http {port}")
    print(f"\n  Then set in Vapi dashboard:")
    print(f"  Assistants → Your Assistant → Server URL")
    print(f"  → https://YOUR-NGROK-URL.ngrok.io/vapi-webhook")
    print(f"{'='*40}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
