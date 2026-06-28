"""
dashboard.py  —  Brew Labs Media · Outbound Sales Intelligence
Run:  streamlit run dashboard.py
"""

import os, json, tempfile, requests
import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Brew Labs Media",
    page_icon="🅱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── BRAND THEME ──────────────────────────────────────────────────────────────
ORANGE  = "#FF4D1C"
ORANGE2 = "#FF6B35"
ORANGE3 = "#CC3D16"
BG      = "#000000"
BG2     = "#0A0A0A"
BG3     = "#111111"
CARD    = "#0D0D0D"
CARD2   = "#141414"
BORDER  = "#1C1C1C"
BORDER2 = "#2A2A2A"
WHITE   = "#FFFFFF"
MUTED   = "#555555"
TEXT2   = "#999999"
GREEN   = "#22C55E"
RED     = "#EF4444"
TEAL    = "#2DD4BF"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background: {BG} !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: {WHITE} !important;
}}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stDeployButton {{ visibility: hidden !important; height: 0 !important; }}

.main .block-container {{
    padding: 0 2rem 4rem !important;
    max-width: 100% !important;
}}

section[data-testid="stSidebar"] {{
    background: {BG2} !important;
    border-right: 1px solid {BORDER} !important;
}}
section[data-testid="stSidebar"] * {{ color: {WHITE} !important; }}
section[data-testid="stSidebar"] input {{
    background: {BG3} !important;
    border-color: {BORDER} !important;
    color: {WHITE} !important;
    border-radius: 4px !important;
}}

/* ── KPI Cards ── */
.kpi-row {{
    display: grid;
    gap: 1px;
    background: {BORDER};
    border: 1px solid {BORDER};
    margin-bottom: 1px;
}}
.kpi-row-6 {{ grid-template-columns: repeat(6, 1fr); }}
.kpi-row-4 {{ grid-template-columns: repeat(4, 1fr); }}
.kpi-row-5 {{ grid-template-columns: repeat(5, 1fr); }}
.kpi-row-3 {{ grid-template-columns: repeat(3, 1fr); }}
.kpi-row-2 {{ grid-template-columns: repeat(2, 1fr); }}

.kpi-card {{
    background: {CARD};
    padding: 24px 20px 18px;
    position: relative;
    overflow: hidden;
    transition: background 0.2s ease;
}}
.kpi-card:hover {{
    background: {CARD2};
}}
.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: transparent;
    transition: background 0.2s;
}}
.kpi-card:hover::before {{
    background: {ORANGE};
}}
.kpi-label {{
    font-size: 0.58rem;
    word-break: keep-all;
    white-space: nowrap;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {MUTED};
    margin-bottom: 10px;
}}
.kpi-value {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.6rem;
    line-height: 1;
    letter-spacing: 0.02em;
    color: {WHITE};
    margin-bottom: 6px;
}}
.kpi-value.orange {{ color: {ORANGE}; }}
.kpi-value.teal {{ color: {TEAL}; }}
.kpi-sub {{
    font-size: 0.68rem;
    font-weight: 500;
    color: {TEXT2};
}}
.kpi-sub.up   {{ color: {GREEN}; }}
.kpi-sub.down {{ color: {RED}; }}

/* ── Section headers ── */
.section-hdr {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 40px 0 24px;
}}
.section-hdr-label {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: {MUTED};
    white-space: nowrap;
    text-transform: uppercase;
}}
.section-hdr-line {{
    flex: 1;
    height: 1px;
    background: {BORDER};
}}

/* ── Chart wrapper ── */
.chart-box {{
    background: {CARD};
    border: 1px solid {BORDER};
    padding: 24px 20px 16px;
    position: relative;
}}
.chart-box-title {{
    font-size: 0.58rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {MUTED};
    margin-bottom: 16px;
}}

/* ── Topbar ── */
.topbar {{
    background: {BG};
    border-bottom: 1px solid {BORDER};
    padding: 0;
    margin: 0 -2rem;
    display: flex;
    align-items: stretch;
}}
.topbar-logo {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 28px;
    border-right: 1px solid {BORDER};
}}
.logo-box {{
    width: 36px; height: 36px;
    background: {ORANGE};
    display: flex; align-items: center; justify-content: center;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.2rem;
    color: {WHITE};
    flex-shrink: 0;
}}
.logo-text {{
    display: flex; flex-direction: column; gap: 0;
}}
.logo-text-top {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 0.95rem;
    letter-spacing: 0.14em;
    color: {WHITE};
    line-height: 1;
}}
.logo-text-bot {{
    font-size: 0.5rem;
    font-weight: 700;
    letter-spacing: 0.25em;
    color: {MUTED};
    text-transform: uppercase;
}}
.topbar-center {{
    flex: 1;
    display: flex;
    align-items: center;
    padding: 0 28px;
}}
.topbar-title {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem;
    letter-spacing: 0.22em;
    color: {MUTED};
}}
.topbar-right {{
    display: flex;
    align-items: center;
    gap: 0;
    border-left: 1px solid {BORDER};
}}
.topbar-stat {{
    padding: 0 24px;
    border-right: 1px solid {BORDER};
    height: 100%;
    display: flex; flex-direction: column;
    justify-content: center;
    gap: 3px;
}}
.topbar-stat-val {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    letter-spacing: 0.04em;
    color: {WHITE};
    line-height: 1;
}}
.topbar-stat-val.orange {{ color: {ORANGE}; }}
.topbar-stat-label {{
    font-size: 0.48rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {MUTED};
}}

/* ── Live pill ── */
.live-pill {{
    display: flex; align-items: center; gap: 8px;
    padding: 0 24px;
}}
.live-dot {{
    width: 7px; height: 7px;
    background: {RED};
    border-radius: 50%;
    animation: pulse-dot 2s infinite;
}}
@keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }}
    50% {{ opacity: 0.7; box-shadow: 0 0 0 6px rgba(239,68,68,0); }}
}}
.live-text {{
    font-size: 0.55rem;
    font-weight: 800;
    letter-spacing: 0.2em;
    color: {RED};
}}

/* ── Insight bar ── */
.insight-bar {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-top: 2px solid {ORANGE};
    padding: 14px 24px;
    font-size: 0.72rem;
    color: {TEXT2};
    letter-spacing: 0.04em;
    margin-top: 1px;
}}
.insight-bar strong {{ color: {ORANGE}; }}

/* ── AB comparison ── */
.ab-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    padding: 24px;
    text-align: center;
}}
.ab-card.winner {{
    border-color: {ORANGE};
    border-top: 2px solid {ORANGE};
}}
.ab-label {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    color: {WHITE};
    margin-bottom: 4px;
}}
.ab-label.orange {{ color: {ORANGE}; }}
.ab-sub {{
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: {MUTED};
    margin-bottom: 16px;
}}
.ab-metric {{
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid {BORDER};
    font-size: 0.78rem;
}}
.ab-metric:last-child {{ border-bottom: none; }}
.ab-metric-label {{ color: {TEXT2}; }}
.ab-metric-val {{ color: {WHITE}; font-weight: 700; }}
.ab-metric-val.orange {{ color: {ORANGE}; }}
.ab-metric-val.green {{ color: {GREEN}; }}

/* ── Pipeline ── */
.pipe-stage {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 20px;
    background: {CARD};
    border: 1px solid {BORDER};
    margin-bottom: 1px;
}}
.pipe-num {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: {ORANGE};
    min-width: 60px;
    text-align: center;
}}
.pipe-bar-bg {{
    flex: 1;
    height: 6px;
    background: {BORDER};
    border-radius: 3px;
    overflow: hidden;
}}
.pipe-bar-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
}}
.pipe-label {{
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {MUTED};
    min-width: 100px;
}}

/* ── Divider ── */
hr {{ border: none !important; border-top: 1px solid {BORDER} !important; margin: 0 !important; }}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {{ background: {CARD} !important; }}

/* ── Mobile responsive ── */
@media (max-width: 768px) {{
    .topbar {{ flex-wrap: wrap; }}
    .topbar-right {{ display: none; }}
    .topbar-center {{ padding: 0 16px; }}
    .topbar-logo {{ padding: 14px 16px; }}
    .main .block-container {{ padding: 0 1rem 3rem !important; }}
    .kpi-row-6 {{ grid-template-columns: repeat(3, 1fr); }}
    .kpi-row-5 {{ grid-template-columns: repeat(2, 1fr); }}
    .kpi-row-4 {{ grid-template-columns: repeat(2, 1fr); }}
    .kpi-row-3 {{ grid-template-columns: repeat(1, 1fr); }}
    .kpi-value {{ font-size: 2rem; }}
    .section-hdr {{ padding: 28px 0 16px; }}
    .ab-card {{ padding: 16px; }}
    .pipe-stage {{ flex-wrap: wrap; gap: 8px; }}
    .pipe-label {{ min-width: auto; }}
}}
@media (max-width: 480px) {{
    .kpi-row-6 {{ grid-template-columns: repeat(2, 1fr); }}
    .kpi-value {{ font-size: 1.6rem; }}
    .kpi-label {{ font-size: 0.5rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
def plot_layout(**kwargs):
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=MUTED, size=11),
        margin=dict(t=8, b=8, l=0, r=0),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(showgrid=False, color=MUTED, linecolor=BORDER, tickcolor=BORDER),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=MUTED, linecolor=BORDER, tickcolor=BORDER),
    )
    base.update(kwargs)
    return base

def section(label):
    st.markdown(f"""
    <div class="section-hdr">
        <span class="section-hdr-label">[ {label} ]</span>
        <div class="section-hdr-line"></div>
    </div>""", unsafe_allow_html=True)

def chart_box(title, fig, height=300):
    st.markdown(f'<div class="chart-box"><div class="chart-box-title">{title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=title)
    st.markdown("</div>", unsafe_allow_html=True)

def kpi(label, value, sub="", orange=False, teal=False, sub_type=""):
    oc = "orange" if orange else ("teal" if teal else "")
    sc = f' {sub_type}' if sub_type else ""
    return f"""<div class="kpi-card"><div class="kpi-label">{label}</div>
    <div class="kpi-value {oc}">{value}</div>
    {"" if not sub else f'<div class="kpi-sub{sc}">{sub}</div>'}
    </div>"""

def empty_state(msg="No Data Yet"):
    st.markdown(f'<div class="chart-box" style="height:280px;display:flex;align-items:center;justify-content:center;color:{MUTED};font-size:0.7rem;letter-spacing:0.15em;text-transform:uppercase;">{msg}</div>', unsafe_allow_html=True)

# ── Data loading ─────────────────────────────────────────────────────────────
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
TOKEN_FILE = "token.json"
SHEET_NAME = "Sales Calls"
C = {
    "ts": "Timestamp", "name": "Name", "company": "Company",
    "status": "Call Status", "outcome": "Outcome", "interested": "Interested",
    "pain": "Pain Point", "duration": "Duration (s)",
    "summary": "Call Summary", "transcript": "Full Transcript",
    "meet": "Google Meet Link", "variant": "Variant",
    "score": "Lead Score", "retry": "Retry Count",
    "followup": "Follow-up Status", "email": "Prospect Email",
}
OUTCOME_MAP = {
    "booked_call": "Booked", "not_interested": "Not Interested",
    "follow_up_email": "Follow-up", "callback_requested": "Callback",
    "voicemail": "Voicemail", "unknown": "Unknown", "": "Pending",
}

@st.cache_data(ttl=60, show_spinner=False)
def load_sheet():
    sheet_id  = os.getenv("GOOGLE_SHEET_ID", "")
    token_path = TOKEN_FILE
    if not os.path.exists(TOKEN_FILE) and os.getenv("GOOGLE_TOKEN_JSON"):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(os.getenv("GOOGLE_TOKEN_JSON")); tmp.close()
        token_path = tmp.name
    elif not os.path.exists(TOKEN_FILE) and hasattr(st, "secrets") and "GOOGLE_TOKEN_JSON" in st.secrets:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(st.secrets["GOOGLE_TOKEN_JSON"]); tmp.close()
        token_path = tmp.name
    elif not os.path.exists(TOKEN_FILE) and hasattr(st, "secrets") and "google_token" in st.secrets:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tok = {k: (list(v) if hasattr(v,"__iter__") and not isinstance(v,str) else str(v)) for k,v in st.secrets["google_token"].items()}
        json.dump(tok, tmp); tmp.close()
        token_path = tmp.name
    if not os.path.exists(token_path):
        return pd.DataFrame()
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        client = gspread.authorize(creds)
        ws      = client.open_by_key(sheet_id).worksheet(SHEET_NAME)
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        if C["ts"] in df.columns:
            df[C["ts"]] = pd.to_datetime(df[C["ts"]], errors="coerce")
        if C["duration"] in df.columns:
            df[C["duration"]] = pd.to_numeric(df[C["duration"]], errors="coerce").fillna(0)
        if C["score"] in df.columns:
            df[C["score"]] = pd.to_numeric(df[C["score"]], errors="coerce").fillna(0)
        if C["retry"] in df.columns:
            df[C["retry"]] = pd.to_numeric(df[C["retry"]], errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"Sheet error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def load_leads_sheet():
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    token_path = TOKEN_FILE
    if not os.path.exists(token_path):
        return pd.DataFrame()
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        client = gspread.authorize(creds)
        ws = client.open_by_key(sheet_id).worksheet("Leads")
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def vapi_spend(days):
    key = os.getenv("VAPI_API_KEY", "")
    if not key: return 0.0
    try:
        since = (datetime.utcnow()-timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        total, page = 0.0, 1
        while True:
            r = requests.get("https://api.vapi.ai/call",
                headers={"Authorization": f"Bearer {key}"},
                params={"limit":100,"page":page,"createdAtGt":since}, timeout=10)
            if not r.ok: break
            calls = r.json()
            if not calls: break
            for c in calls: total += float(c.get("cost") or 0)
            if len(calls) < 100: break
            page += 1
        return round(total, 4)
    except: return 0.0

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.2rem;letter-spacing:0.12em;color:{ORANGE};margin-bottom:4px;'>Settings</div>", unsafe_allow_html=True)
    deal_value    = st.number_input("Avg deal value ($/mo)", 0, 100000, 2000, 100)
    cost_per_lead = st.number_input("Research cost/lead ($)", 0.0, 1.0, 0.01, 0.001, format="%.3f")
    st.divider()
    st.markdown(f"<div style='font-size:0.65rem;color:{MUTED};margin-top:4px;'>Use the date filter in the top bar to change the reporting period.</div>", unsafe_allow_html=True)
    st.divider()
    if st.button("↺  REFRESH", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown(f"<div style='font-size:0.65rem;color:{MUTED};margin-top:12px;'>Auto-refresh · 60s<br>Last: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# ── Date filter ──────────────────────────────────────────────────────────────
now = datetime.now()
with st.spinner(""):
    df_all = load_sheet()
    df_leads = load_leads_sheet()

# Default: last 30 days
default_start = (now - timedelta(days=30)).date()
default_end = now.date()

if not df_all.empty and C["ts"] in df_all.columns:
    df = df_all.copy()
else:
    df = df_all.copy()
has = not df.empty

# ── TOP BAR ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar">
    <div class="topbar-logo">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="36" height="36" style="flex-shrink:0;">
          <rect width="64" height="64" fill="{ORANGE}"/>
          <g fill="none" stroke="#000" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12v16a10 10 0 0 0 20 0V12"/>
            <path d="M17 52h30"/>
            <path d="M27 36c-5 3 -7 7 -7 14"/>
            <path d="M37 36c5 3 7 7 7 14"/>
          </g>
        </svg>
        <div class="logo-text">
            <div class="logo-text-top">BREW LABS</div>
            <div class="logo-text-bot">MEDIA</div>
        </div>
    </div>
    <div class="topbar-center">
        <span class="topbar-title">Outbound Sales Intelligence</span>
    </div>
    <div class="topbar-right">
        <div class="live-pill">
            <div class="live-dot"></div>
            <span class="live-text">LIVE</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Date range filter (top bar style) ────────────────────────────────────────
fr_spacer, fr_select = st.columns([5, 2])
with fr_select:
    range_opt = st.selectbox("", ["This Month", "Last Month", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time", "Custom"], label_visibility="collapsed", key="range_sel")

if range_opt == "Custom":
    _, cr1, cr2, _ = st.columns([3, 2, 2, 3])
    with cr1:
        date_start = st.date_input("From", value=default_start, max_value=now.date(), key="ds")
    with cr2:
        date_end = st.date_input("To", value=default_end, max_value=now.date(), key="de")
else:
    date_end = now.date()
    if range_opt == "This Month":
        date_start = now.replace(day=1).date()
    elif range_opt == "Last Month":
        first_this = now.replace(day=1)
        last_month_end = first_this - timedelta(days=1)
        date_start = last_month_end.replace(day=1).date()
        date_end = last_month_end.date()
    elif range_opt == "Last 7 Days":
        date_start = (now - timedelta(days=7)).date()
    elif range_opt == "Last 30 Days":
        date_start = (now - timedelta(days=30)).date()
    elif range_opt == "Last 90 Days":
        date_start = (now - timedelta(days=90)).date()
    else:
        date_start = datetime(2000, 1, 1).date()

# Apply date filter
if has and C["ts"] in df.columns:
    df = df[(df[C["ts"]] >= pd.Timestamp(date_start)) & (df[C["ts"]] <= pd.Timestamp(datetime.combine(date_end, datetime.max.time())))].copy()
    has = not df.empty

days_back = max((date_end - date_start).days, 1)

# Recompute KPIs with filtered data
total  = len(df)
connected = int(df[C["status"]].str.lower().isin(["completed","ended"]).sum()) if has and C["status"] in df.columns else total

bookings = follow_ups = callbacks = not_int = voicemails = 0
if has and C["outcome"] in df.columns:
    oc = df[C["outcome"]].str.lower().str.strip()
    bookings   = int((oc=="booked_call").sum())
    follow_ups = int((oc=="follow_up_email").sum())
    callbacks  = int((oc=="callback_requested").sum())
    voicemails = int((oc=="voicemail").sum())
    not_int    = int((oc=="not_interested").sum())

interested  = bookings + follow_ups + callbacks
answer_rate = (connected/total*100) if total else 0
conv_rate   = (bookings/connected*100) if connected else 0
avg_dur     = df[C["duration"]].mean() if has and C["duration"] in df.columns else 0

api_spend      = vapi_spend(days_back)
research_spend = round(total * cost_per_lead, 2)
total_cost     = round(api_spend + research_spend, 2)
revenue        = bookings * deal_value
profit         = revenue - total_cost
roi            = ((profit/total_cost)*100) if total_cost else 0
cpb            = (total_cost/bookings) if bookings else 0

if bookings > 0:
    st.markdown(f'<div class="insight-bar">[ PERFORMANCE ] &nbsp; Cost per booking: <strong>${cpb:.2f}</strong> &nbsp;·&nbsp; {bookings} bookings × ${deal_value:,}/mo = <strong>${revenue:,.0f}</strong> pipeline &nbsp;·&nbsp; ROI: <strong>{roi:.0f}%</strong></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 01 / CALL PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
section("01 / CALL PERFORMANCE")

st.markdown(
    '<div class="kpi-row kpi-row-6">' +
    kpi("Calls Made",     f"{total:,}",             "period total") +
    kpi("Connected",      f"{connected:,}",          f"{answer_rate:.0f}% answer rate", sub_type="up" if answer_rate>30 else "") +
    kpi("Bookings",       f"{bookings:,}",           "discovery calls", orange=True) +
    kpi("Conversion",     f"{conv_rate:.1f}%",       "booked ÷ connected", sub_type="up" if conv_rate>5 else "") +
    kpi("Follow-ups",     f"{follow_ups:,}",         "email requested") +
    kpi("Avg Duration",   f"{avg_dur:.0f}s" if avg_dur else "—", "per call") +
    '</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# 02 / FINANCIALS
# ══════════════════════════════════════════════════════════════════════════════
section("02 / FINANCIALS")

st.markdown(
    '<div class="kpi-row kpi-row-6">' +
    kpi("Vapi Spend",     f"${api_spend:.2f}",       "live from API") +
    kpi("Research Spend", f"${research_spend:.2f}",   f"{total} leads") +
    kpi("Total Cost",     f"${total_cost:.2f}",       "all APIs", sub_type="down" if total_cost>0 else "") +
    kpi("Revenue",        f"${revenue:,.0f}",         f"{bookings} × ${deal_value:,}", orange=True, sub_type="up" if revenue>0 else "") +
    kpi("Net Profit",     f"${profit:,.0f}",          "revenue − cost", sub_type="up" if profit>=0 else "down") +
    kpi("ROI",            f"{roi:.0f}%",              "return on spend", orange=roi>=0, sub_type="up" if roi>=0 else "down") +
    '</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# 03 / ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
section("03 / ANALYTICS")

col1, col2 = st.columns([3, 2])

with col1:
    if has and C["ts"] in df.columns:
        daily = (df.dropna(subset=[C["ts"]])
                   .groupby(df[C["ts"]].dt.strftime("%Y-%m-%d")).size()
                   .reset_index(name="Calls")
                   .rename(columns={C["ts"]: "Date"}))
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily["Date"], y=daily["Calls"],
            marker=dict(color=ORANGE, opacity=0.85, line=dict(color=ORANGE2, width=0)),
            hovertemplate="<b>%{x}</b><br>%{y} calls<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=daily["Date"], y=daily["Calls"],
            mode="lines", line=dict(color=WHITE, width=1.5, dash="dot"),
            hoverinfo="skip",
        ))
        fig.update_layout(**plot_layout(height=300,
            xaxis=dict(showgrid=False, color=MUTED, linecolor=BORDER),
            yaxis=dict(showgrid=True, gridcolor=BORDER, color=MUTED, linecolor=BORDER),
        ))
        chart_box("Calls Over Time", fig)
    else:
        empty_state()

with col2:
    if has and C["outcome"] in df.columns and total > 0:
        oc_cnt = df[C["outcome"]].str.lower().str.strip().value_counts().reset_index()
        oc_cnt.columns = ["outcome","count"]
        oc_cnt["label"] = oc_cnt["outcome"].map(lambda x: OUTCOME_MAP.get(x, x.title()))
        colors = [ORANGE, ORANGE2, ORANGE3, BORDER2, BORDER, BG3]
        fig2 = go.Figure(go.Pie(
            labels=oc_cnt["label"], values=oc_cnt["count"],
            hole=0.65,
            marker=dict(colors=colors[:len(oc_cnt)], line=dict(color=BG, width=3)),
            textinfo="percent",
            textfont=dict(color=WHITE, size=11),
            hovertemplate="<b>%{label}</b><br>%{value} calls<extra></extra>",
        ))
        fig2.add_annotation(
            text=f"<b style='font-size:22px'>{total}</b><br><span style='font-size:10px;color:{MUTED}'>CALLS</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color=WHITE, size=14, family="Bebas Neue"),
        )
        fig2.update_layout(**plot_layout(height=300, showlegend=True,
            legend=dict(orientation="v", x=1.02, y=0.5,
                        font=dict(color=TEXT2, size=10),
                        bgcolor="rgba(0,0,0,0)"),
        ))
        chart_box("Outcome Breakdown", fig2)
    else:
        empty_state()

c3, c4 = st.columns(2)
with c3:
    stages = ["Calls Made","Connected","Interested","Booked"]
    vals   = [total, connected, interested, bookings]
    fig3 = go.Figure(go.Funnel(
        y=stages, x=vals,
        textinfo="value+percent initial",
        textfont=dict(color=WHITE, size=12, family="Inter"),
        marker=dict(
            color=[BORDER2, BG3, ORANGE2, ORANGE],
            line=dict(color=BG, width=2),
        ),
        connector=dict(line=dict(color=BORDER, width=1)),
        hovertemplate="<b>%{label}</b><br>%{value}<extra></extra>",
    ))
    fig3.update_layout(**plot_layout(height=280, showlegend=False,
        yaxis=dict(color=MUTED, showgrid=False),
    ))
    chart_box("Conversion Funnel", fig3)

with c4:
    categories = ["Revenue", "Vapi Spend", "Research"]
    values     = [revenue, api_spend, research_spend]
    bar_colors = [ORANGE, BORDER2, BORDER]
    fig4 = go.Figure(go.Bar(
        x=categories, y=values,
        marker=dict(color=bar_colors, line=dict(color=[ORANGE2, BG3, BG3], width=1)),
        text=[f"${v:,.2f}" for v in values],
        textposition="outside",
        textfont=dict(color=TEXT2, size=11),
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    fig4.update_layout(**plot_layout(height=280,
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=MUTED),
    ))
    chart_box("Revenue vs Cost", fig4)

# ══════════════════════════════════════════════════════════════════════════════
# 03.5 / MONTHLY BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
section("03B / MONTHLY PERFORMANCE")

if has and C["ts"] in df_all.columns:
    mdf = df_all.dropna(subset=[C["ts"]]).copy()
    mdf["month"] = mdf[C["ts"]].dt.to_period("M").astype(str)

    monthly_rows = []
    for month in sorted(mdf["month"].unique()):
        m = mdf[mdf["month"]==month]
        mt = len(m)
        mc = int(m[C["status"]].str.lower().isin(["completed","ended"]).sum()) if C["status"] in m.columns else mt
        mb = int((m[C["outcome"]].str.lower().str.strip()=="booked_call").sum()) if C["outcome"] in m.columns else 0
        mfu = int((m[C["outcome"]].str.lower().str.strip()=="follow_up_email").sum()) if C["outcome"] in m.columns else 0
        mvm = int((m[C["outcome"]].str.lower().str.strip()=="voicemail").sum()) if C["outcome"] in m.columns else 0
        mar = round(mc/mt*100,1) if mt else 0
        mcr = round(mb/mc*100,1) if mc else 0
        mdur = round(m[C["duration"]].mean(),0) if C["duration"] in m.columns else 0
        monthly_rows.append({
            "Month": month, "Calls": mt, "Connected": mc,
            "Answer %": f"{mar}%", "Bookings": mb, "Conv %": f"{mcr}%",
            "Follow-ups": mfu, "Voicemails": mvm, "Avg Duration": f"{mdur:.0f}s",
        })

    monthly_df = pd.DataFrame(monthly_rows)

    # Monthly bar chart
    m_months = [r["Month"] for r in monthly_rows]
    m_calls = [r["Calls"] for r in monthly_rows]
    m_bookings = [r["Bookings"] for r in monthly_rows]

    fig_m = go.Figure()
    fig_m.add_trace(go.Bar(
        name="Calls", x=m_months, y=m_calls,
        marker=dict(color=BORDER2, opacity=0.9),
        hovertemplate="<b>%{x}</b><br>%{y} calls<extra></extra>",
    ))
    fig_m.add_trace(go.Bar(
        name="Bookings", x=m_months, y=m_bookings,
        marker=dict(color=ORANGE, opacity=0.9),
        hovertemplate="<b>%{x}</b><br>%{y} bookings<extra></extra>",
    ))
    fig_m.update_layout(**plot_layout(height=280, showlegend=True, barmode="group",
        legend=dict(orientation="h", x=0, y=1.15, font=dict(color=TEXT2, size=10), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, color=MUTED, linecolor=BORDER),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=MUTED, linecolor=BORDER),
    ))
    chart_box("Monthly Calls vs Bookings", fig_m)

    # Monthly table
    st.dataframe(monthly_df, use_container_width=True, hide_index=True,
        column_config={
            "Month": st.column_config.TextColumn("Month"),
            "Calls": st.column_config.NumberColumn("Calls"),
            "Bookings": st.column_config.NumberColumn("Bookings"),
        },
    )
else:
    empty_state("Monthly data appears after calls are logged")

# ══════════════════════════════════════════════════════════════════════════════
# 04 / A·B TESTING
# ══════════════════════════════════════════════════════════════════════════════
section("04 / A·B TESTING")

has_ab = has and C["variant"] in df.columns and df[C["variant"]].isin(["A","B"]).any()

if has_ab:
    va = df[df[C["variant"]]=="A"]
    vb = df[df[C["variant"]]=="B"]

    def ab_stats(d):
        t = len(d)
        c = int(d[C["status"]].str.lower().isin(["completed","ended"]).sum()) if C["status"] in d.columns else t
        b = int((d[C["outcome"]].str.lower().str.strip()=="booked_call").sum()) if C["outcome"] in d.columns else 0
        i = int((d[C["interested"]].str.lower()=="yes").sum()) if C["interested"] in d.columns else 0
        return {"total": t, "connected": c, "booked": b, "interested": i,
                "interest_pct": round(i/c*100,1) if c else 0,
                "booking_pct": round(b/c*100,1) if c else 0}

    sa, sb = ab_stats(va), ab_stats(vb)
    a_wins = sa["booking_pct"] >= sb["booking_pct"]

    ca, cb = st.columns(2)
    with ca:
        w = "winner" if a_wins else ""
        st.markdown(f"""<div class="ab-card {w}">
            <div class="ab-label {'orange' if a_wins else ''}">VARIANT A</div>
            <div class="ab-sub">{"◆ WINNING" if a_wins else "CHALLENGER"}</div>
            <div class="ab-metric"><span class="ab-metric-label">Total Calls</span><span class="ab-metric-val">{sa['total']}</span></div>
            <div class="ab-metric"><span class="ab-metric-label">Connected</span><span class="ab-metric-val">{sa['connected']}</span></div>
            <div class="ab-metric"><span class="ab-metric-label">Interested</span><span class="ab-metric-val {'green' if sa['interest_pct']>sb['interest_pct'] else ''}">{sa['interested']} ({sa['interest_pct']}%)</span></div>
            <div class="ab-metric"><span class="ab-metric-label">Bookings</span><span class="ab-metric-val {'orange' if a_wins else ''}">{sa['booked']} ({sa['booking_pct']}%)</span></div>
        </div>""", unsafe_allow_html=True)

    with cb:
        w = "winner" if not a_wins else ""
        st.markdown(f"""<div class="ab-card {w}">
            <div class="ab-label {'orange' if not a_wins else ''}">VARIANT B</div>
            <div class="ab-sub">{"◆ WINNING" if not a_wins else "CHALLENGER"}</div>
            <div class="ab-metric"><span class="ab-metric-label">Total Calls</span><span class="ab-metric-val">{sb['total']}</span></div>
            <div class="ab-metric"><span class="ab-metric-label">Connected</span><span class="ab-metric-val">{sb['connected']}</span></div>
            <div class="ab-metric"><span class="ab-metric-label">Interested</span><span class="ab-metric-val {'green' if sb['interest_pct']>sa['interest_pct'] else ''}">{sb['interested']} ({sb['interest_pct']}%)</span></div>
            <div class="ab-metric"><span class="ab-metric-label">Bookings</span><span class="ab-metric-val {'orange' if not a_wins else ''}">{sb['booked']} ({sb['booking_pct']}%)</span></div>
        </div>""", unsafe_allow_html=True)

    min_calls = min(sa["total"], sb["total"])
    if min_calls < 30:
        st.markdown(f'<div style="text-align:center;padding:12px;font-size:0.7rem;color:{MUTED};letter-spacing:0.1em;text-transform:uppercase;">Need {30-min_calls} more calls per variant for statistical significance</div>', unsafe_allow_html=True)
else:
    empty_state("A/B data will appear after calls with variant assignment")

# ══════════════════════════════════════════════════════════════════════════════
# 05 / LEAD SCORING
# ══════════════════════════════════════════════════════════════════════════════
section("05 / LEAD SCORING")

has_score = has and C["score"] in df.columns and df[C["score"]].sum() > 0

if has_score:
    scores = df[df[C["score"]]>0]

    s1, s2 = st.columns([3, 2])
    with s1:
        fig_score = go.Figure()
        fig_score.add_trace(go.Histogram(
            x=scores[C["score"]],
            nbinsx=10,
            marker=dict(color=ORANGE, opacity=0.85, line=dict(color=ORANGE2, width=1)),
            hovertemplate="Score %{x}<br>%{y} leads<extra></extra>",
        ))
        fig_score.update_layout(**plot_layout(height=260,
            xaxis=dict(title="Lead Score", showgrid=False, color=MUTED, linecolor=BORDER),
            yaxis=dict(title="Leads", showgrid=True, gridcolor=BORDER, color=MUTED, linecolor=BORDER),
        ))
        chart_box("Score Distribution", fig_score)

    with s2:
        brackets = [(0,30,"0-30"),(31,60,"31-60"),(61,80,"61-80"),(81,100,"81-100")]
        bracket_data = []
        for lo, hi, label in brackets:
            b = scores[(scores[C["score"]]>=lo) & (scores[C["score"]]<=hi)]
            bt = len(b)
            bb = int((b[C["outcome"]].str.lower().str.strip()=="booked_call").sum()) if C["outcome"] in b.columns and bt > 0 else 0
            bracket_data.append({"bracket": label, "leads": bt, "booked": bb, "rate": round(bb/bt*100,1) if bt else 0})

        fig_br = go.Figure()
        fig_br.add_trace(go.Bar(
            x=[b["bracket"] for b in bracket_data],
            y=[b["rate"] for b in bracket_data],
            marker=dict(color=[BORDER2, BORDER2, ORANGE2, ORANGE]),
            text=[f"{b['rate']}%" for b in bracket_data],
            textposition="outside",
            textfont=dict(color=TEXT2, size=11),
            hovertemplate="<b>Score %{x}</b><br>Booking rate: %{y:.1f}%<extra></extra>",
        ))
        fig_br.update_layout(**plot_layout(height=260,
            xaxis=dict(title="Score Bracket", showgrid=False, color=MUTED, linecolor=BORDER),
            yaxis=dict(title="Booking %", showgrid=True, gridcolor=BORDER, color=MUTED, linecolor=BORDER),
        ))
        chart_box("Conversion by Score", fig_br)

    avg_score = scores[C["score"]].mean()
    med_score = scores[C["score"]].median()
    top_score = scores[C["score"]].max()
    st.markdown(
        '<div class="kpi-row kpi-row-3">' +
        kpi("Avg Score", f"{avg_score:.0f}", "across all leads") +
        kpi("Median", f"{med_score:.0f}", "middle value") +
        kpi("Top Score", f"{top_score:.0f}", "best lead", orange=True) +
        '</div>',
        unsafe_allow_html=True,
    )
else:
    empty_state("Scores appear after running research with lead scoring")

# ══════════════════════════════════════════════════════════════════════════════
# 06 / LEAD PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
section("06 / LEAD PIPELINE")

if not df_leads.empty and "Status" in df_leads.columns:
    status_counts = df_leads["Status"].str.lower().value_counts()
    new_c = int(status_counts.get("new", 0))
    researched_c = int(status_counts.get("researched", 0))
    called_c = total
    booked_c = bookings

    pipe_total = max(new_c + researched_c + called_c, 1)
    stages_pipe = [
        ("New Leads", new_c, TEAL),
        ("Researched", researched_c, ORANGE2),
        ("Called", called_c, ORANGE),
        ("Booked", booked_c, GREEN),
    ]

    for label, count, color in stages_pipe:
        pct = count / pipe_total * 100
        st.markdown(f"""<div class="pipe-stage">
            <div class="pipe-label">{label}</div>
            <div class="pipe-num">{count}</div>
            <div class="pipe-bar-bg">
                <div class="pipe-bar-fill" style="width:{pct}%;background:{color};"></div>
            </div>
        </div>""", unsafe_allow_html=True)
else:
    empty_state("Pipeline data appears after importing leads to Sheets")

# ══════════════════════════════════════════════════════════════════════════════
# 07 / RETRY & FOLLOW-UP
# ══════════════════════════════════════════════════════════════════════════════
section("07 / RETRY & FOLLOW-UP")

has_retry = has and C["retry"] in df.columns
has_followup = has and C["followup"] in df.columns

if has_retry or has_followup:
    pending_retries = int((df[C["retry"]]>0).sum()) if has_retry else 0
    max_retries = int(df[C["retry"]].max()) if has_retry else 0

    emails_sent = 0
    callbacks_scheduled = 0
    followups_completed = 0
    if has_followup:
        fu = df[C["followup"]].str.lower().str.strip()
        emails_sent = int((fu=="sent").sum())
        callbacks_scheduled = int((fu=="callback_scheduled").sum())
        followups_completed = int((fu=="completed").sum())

    st.markdown(
        '<div class="kpi-row kpi-row-5">' +
        kpi("Retried Calls", f"{pending_retries}", f"max {max_retries} retries") +
        kpi("Voicemails", f"{voicemails}", "eligible for retry") +
        kpi("Emails Sent", f"{emails_sent}", "follow-up emails", teal=True) +
        kpi("Callbacks Due", f"{callbacks_scheduled}", "scheduled", orange=True) +
        kpi("Completed", f"{followups_completed}", "follow-ups done", sub_type="up" if followups_completed>0 else "") +
        '</div>',
        unsafe_allow_html=True,
    )
else:
    empty_state("Retry & follow-up data appears after calls with v2 features")

# ══════════════════════════════════════════════════════════════════════════════
# 08 / ROI PROJECTOR
# ══════════════════════════════════════════════════════════════════════════════
section("08 / ROI PROJECTOR")

st.markdown(f'<div style="background:{CARD};border:1px solid {BORDER};padding:24px 28px 28px;">', unsafe_allow_html=True)
s1, s2, s3 = st.columns(3)
with s1: pc = st.slider("Calls / month",    10, 500, max(total or 50, 50), 10)
with s2: pa = st.slider("Answer rate (%)",   5,  80, max(int(answer_rate or 30), 5))
with s3: pv = st.slider("Booking rate (%)", 1,  40, max(int(conv_rate or 5), 1))

p_conn  = int(pc * pa / 100)
p_book  = int(p_conn * pv / 100)
p_rev   = p_book * deal_value
p_cost  = round(pc * (api_spend/total if total else 0.08) + pc*cost_per_lead, 2)
p_roi   = ((p_rev-p_cost)/p_cost*100) if p_cost else 0

st.markdown(f'<div style="height:16px"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="kpi-row kpi-row-4">' +
    kpi("Proj. Connected",  f"{p_conn:,}",           f"{pa}% of {pc} calls") +
    kpi("Proj. Bookings",   f"{p_book:,}",            f"{pv}% conversion", orange=True) +
    kpi("Proj. Revenue",    f"${p_rev:,.0f}",         f"{p_book} × ${deal_value:,}", orange=True) +
    kpi("Proj. ROI",        f"{min(p_roi,9999):.0f}%{'⁺' if p_roi>9999 else ''}",  f"net ${p_rev-p_cost:,.0f}", orange=p_roi>=0, sub_type="up" if p_roi>=0 else "down") +
    '</div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 09 / RECENT CALLS
# ══════════════════════════════════════════════════════════════════════════════
section("09 / RECENT CALLS")

if has:
    show_cols = [C[k] for k in ["ts","name","company","status","outcome","interested","score","variant","pain","duration","meet"] if C.get(k) and C[k] in df.columns]
    disp = df.sort_values(C["ts"], ascending=False).head(30)[show_cols].copy()
    if C["ts"] in disp.columns:
        disp[C["ts"]] = disp[C["ts"]].dt.strftime("%d %b %Y  %H:%M")
    if C["outcome"] in disp.columns:
        disp[C["outcome"]] = disp[C["outcome"]].map(lambda x: OUTCOME_MAP.get(str(x).lower().strip(), x))

    st.dataframe(disp, use_container_width=True, hide_index=True,
        column_config={
            C["meet"]:     st.column_config.LinkColumn("Meet Link"),
            C["duration"]: st.column_config.NumberColumn("Duration", format="%d s"),
            C["ts"]:       st.column_config.TextColumn("Time"),
            C["score"]:    st.column_config.NumberColumn("Score", format="%d"),
        },
    )

    with st.expander("VIEW TRANSCRIPT"):
        if C["transcript"] in df.columns:
            opts = df.sort_values(C["ts"], ascending=False).head(20)
            sel  = st.selectbox("Select call", opts.index,
                format_func=lambda i: f"{df.loc[i,C['name']]}  ·  {df.loc[i,C['ts']].strftime('%d %b %Y %H:%M') if pd.notna(df.loc[i,C['ts']]) else '—'}" if C["name"] in df.columns else str(i))
            if sel is not None:
                row = df.loc[sel]
                if row.get(C["summary"]):
                    st.markdown(f'<div style="background:{BG3};border-left:3px solid {ORANGE};padding:14px 18px;margin-bottom:12px;font-size:0.83rem;color:{TEXT2};line-height:1.6;"><strong style="color:{ORANGE};font-size:0.62rem;letter-spacing:0.1em;text-transform:uppercase;display:block;margin-bottom:6px;">Summary</strong>{row.get(C["summary"],"")}</div>', unsafe_allow_html=True)
                st.text_area("Full Transcript", value=row.get(C["transcript"],"No transcript"), height=280)
else:
    st.markdown(f'<div style="padding:60px 0;text-align:center;color:{MUTED};font-size:0.7rem;letter-spacing:0.15em;text-transform:uppercase;">No calls logged yet · Run your first campaign to begin</div>', unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:64px;border-top:1px solid {BORDER};padding-top:20px;
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div style="display:flex;align-items:center;gap:10px;">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="18" height="18"><rect width="64" height="64" fill="{ORANGE}"/><g fill="none" stroke="#000" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12v16a10 10 0 0 0 20 0V12"/><path d="M17 52h30"/><path d="M27 36c-5 3 -7 7 -7 14"/><path d="M37 36c5 3 7 7 7 14"/></g></svg>
        <span style="font-size:0.58rem;font-weight:700;letter-spacing:0.18em;color:{MUTED};text-transform:uppercase;">Brew Labs Media · Sales Intelligence v2</span>
    </div>
    <span style="font-size:0.58rem;color:{BORDER2};letter-spacing:0.08em;">Data refreshes every 60s</span>
</div>
""", unsafe_allow_html=True)
