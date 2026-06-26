"""
setup_assistant.py
------------------
Creates (or updates) your Vapi AI sales assistant using config/assistant_config.json.
Run this once before making calls.

Usage:
    python setup_assistant.py              # Create a new assistant
    python setup_assistant.py --update ID  # Update an existing assistant by ID
"""

import json
import os
import sys
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_BASE_URL = "https://api.vapi.ai"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "assistant_config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def create_assistant(config: dict) -> dict:
    """POST /assistant — create a new assistant."""
    response = requests.post(
        f"{VAPI_BASE_URL}/assistant",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=config,
    )
    response.raise_for_status()
    return response.json()


def update_assistant(assistant_id: str, config: dict) -> dict:
    """PATCH /assistant/:id — update an existing assistant."""
    response = requests.patch(
        f"{VAPI_BASE_URL}/assistant/{assistant_id}",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=config,
    )
    response.raise_for_status()
    return response.json()


def get_assistant(assistant_id: str) -> dict:
    """GET /assistant/:id — fetch assistant details."""
    response = requests.get(
        f"{VAPI_BASE_URL}/assistant/{assistant_id}",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
    )
    response.raise_for_status()
    return response.json()


def save_assistant_id(assistant_id: str):
    """Persist the assistant ID to .assistant_id for use by run_calls.py."""
    with open(".assistant_id", "w") as f:
        f.write(assistant_id)
    print(f"  Assistant ID saved to .assistant_id")


def main():
    if not VAPI_API_KEY:
        print("ERROR: VAPI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Set up your Vapi sales assistant.")
    parser.add_argument(
        "--update",
        metavar="ASSISTANT_ID",
        help="Update an existing assistant instead of creating a new one.",
    )
    args = parser.parse_args()

    print("Loading assistant config...")
    config = load_config()
    print(f"  Assistant name: {config.get('name')}")

    if args.update:
        print(f"\nUpdating assistant {args.update}...")
        assistant = update_assistant(args.update, config)
        print(f"  Updated successfully.")
    else:
        print("\nCreating new assistant...")
        assistant = create_assistant(config)
        print(f"  Created successfully.")

    assistant_id = assistant["id"]
    print(f"\n{'='*50}")
    print(f"  Assistant ID : {assistant_id}")
    print(f"  Name         : {assistant.get('name')}")
    print(f"  Model        : {assistant.get('model', {}).get('model')}")
    print(f"{'='*50}\n")

    save_assistant_id(assistant_id)
    print("Next step: add your leads to leads.csv, then run:")
    print("  python run_calls.py\n")


if __name__ == "__main__":
    main()
