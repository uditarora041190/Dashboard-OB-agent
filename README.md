# Outbound Sales Agent — AI & Marketing Agency

An AI-powered outbound calling agent built on [Vapi.ai](https://vapi.ai). It places real phone calls, holds dynamic sales conversations using Claude, qualifies leads, and aims to book discovery calls — all without a human on the line.

---

## What It Does

- Calls prospects from your leads list using a natural AI voice
- Holds a consultative, dynamic conversation (not a rigid script)
- Adapts the pitch based on what the prospect says
- Handles common objections naturally
- Tries to book a 15-minute discovery call
- Records every call and auto-generates a summary + structured outcome
- Logs all results to `call_log.csv`

---

## Prerequisites

- Python 3.11+
- A [Vapi.ai](https://vapi.ai) account (free tier available)
- An Anthropic API key (connect in Vapi dashboard under Providers)
- An ElevenLabs account (optional — for the default voice; or swap to a free Vapi voice)

---

## Setup

### 1. Clone / download this project

```bash
cd outbound-sales-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to find it |
|---|---|
| `VAPI_API_KEY` | [dashboard.vapi.ai/account](https://dashboard.vapi.ai/account) |
| `VAPI_PHONE_NUMBER_ID` | Dashboard → Phone Numbers → copy ID |

### 4. Buy a phone number in Vapi

Go to **Dashboard → Phone Numbers → Add Phone Number**. Pick a local US number (~$2/month). Copy its ID into `VAPI_PHONE_NUMBER_ID` in your `.env`.

### 5. Connect your voice provider (optional)

The default config uses ElevenLabs voice `21m00Tcm4TlvDq8ikWAM` (Rachel). To use it:
- Go to **Dashboard → Providers → ElevenLabs** and paste your ElevenLabs API key.

To use a free Vapi-native voice instead, edit `config/assistant_config.json`:
```json
"voice": {
  "provider": "vapi",
  "voiceId": "Elliot"
}
```

### 6. Customize the assistant

Open `config/assistant_config.json` and update:
- `"name"` — the assistant's name (default: "Alex")
- `"firstMessage"` — replace `[Your Agency Name]` with your real agency name
- The `systemPrompt` — replace `[Your Agency Name]` and adjust any services/pricing

### 7. Create your assistant in Vapi

```bash
python setup_assistant.py
```

This uploads your config to Vapi and saves the assistant ID to `.assistant_id`. You only need to run this once (or when you update the config).

To update an existing assistant:
```bash
python setup_assistant.py --update <ASSISTANT_ID>
```

---

## Making Calls

### Prepare your leads

Copy the example file and fill it in:
```bash
cp leads_example.csv leads.csv
```

Edit `leads.csv`:
```csv
name,phone,company,notes
John Smith,+14155552671,Acme Corp,Met at SaaStr; interested in automation
```

**Phone numbers must be in E.164 format:** `+1XXXXXXXXXX` for US numbers.

### Run a dry run first

Preview your leads without making any calls:
```bash
python run_calls.py --dry-run
```

### Make calls

```bash
python run_calls.py           # Call everyone in leads.csv
python run_calls.py --limit 5 # Call only the first 5 leads
```

---

## Monitoring Results

**Live view:** [dashboard.vapi.ai/calls](https://dashboard.vapi.ai/calls) — see calls in real time, listen to recordings, read transcripts and AI summaries.

**Call log:** Results are written to `call_log.csv` as calls are queued:
```
timestamp, name, phone, company, call_id, status, error
```

**Per-call analysis:** Vapi auto-generates (after each call ends):
- A plain-English summary
- Structured outcome data: `interested`, `pain_point`, `outcome`, `callback_time`, `notes`
- A pass/fail success score

You can access these via the dashboard or the Vapi API (`GET /call/:id`).

---

## Customization Tips

### Change the voice
Browse voices at [elevenlabs.io/voice-library](https://elevenlabs.io/voice-library) and paste the voice ID into `assistant_config.json → voice.voiceId`.

### Change the AI model
The default is `claude-3-5-haiku-20241022` for speed and low cost. For more nuanced conversations, switch to `claude-3-5-sonnet-20241022` in `assistant_config.json → model.model`.

### Adjust call timing
Set `CALL_DELAY_SECONDS` in `.env` to control the pause between calls. Default is 5 seconds.

### Add more lead context
The `notes` column in `leads.csv` is injected into the assistant's context for each call — use it to personalize ("warm lead from LinkedIn", "interested in chatbots").

---

## Project Structure

```
outbound-sales-agent/
├── config/
│   └── assistant_config.json   # AI assistant config (voice, prompt, analysis)
├── setup_assistant.py          # Create/update the assistant in Vapi
├── run_calls.py                # Load leads and trigger outbound calls
├── leads_example.csv           # Example leads format
├── leads.csv                   # Your actual leads (create this yourself)
├── call_log.csv                # Auto-generated call log
├── .assistant_id               # Auto-generated after setup_assistant.py
├── .env.example                # Environment variable template
├── .env                        # Your credentials (never commit this)
└── requirements.txt
```

---

## Legal & Compliance

Before making outbound calls, ensure you comply with:
- **TCPA** (US): You must have prior express written consent or an established business relationship before auto-dialing.
- **Do Not Call Registry**: Scrub your list against the national DNC registry.
- **State laws**: Some states (CA, FL, etc.) have stricter telemarketing rules.
- **Call disclosure**: Depending on jurisdiction, the agent may need to disclose it is an AI at the start of the call.

Consider consulting a lawyer before running large-scale campaigns.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `401 Unauthorized` | Check your `VAPI_API_KEY` in `.env` |
| `Phone number not found` | Verify `VAPI_PHONE_NUMBER_ID` matches an active number in your Vapi dashboard |
| `Assistant not found` | Run `python setup_assistant.py` first |
| Call connects but no voice | Check your ElevenLabs API key is connected in Vapi → Providers |
| Phone format warning | Use E.164 format: `+14155552671` not `(415) 555-2671` |
