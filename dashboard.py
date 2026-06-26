"""
dashboard.py  —  Brew Labs Media · Outbound Sales Agent Dashboard
Run:  streamlit run dashboard.py
"""

import os, json, tempfile, requests
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brew Labs Media",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #03020d !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: #e2e8f0 !important;
}

/* Ambient glow background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 50% at 10% 0%,   rgba(109,40,217,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 90% 100%,  rgba(6,182,212,0.12) 0%,  transparent 60%),
        radial-gradient(ellipse 50% 50% at 50% 50%,  rgba(34,197,94,0.04) 0%,  transparent 70%);
    pointer-events: none;
    z-index: 0;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stDeployButton { visibility: hidden !important; height: 0 !important; }

/* Main container */
.main .block-container {
    padding: 2rem 2.5rem 3rem !important;
    max-width: 100% !important;
    position: relative;
    z-index: 1;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(3,2,13,0.97) !important;
    border-right: 1px solid rgba(109,40,217,0.25) !important;
    backdrop-filter: blur(24px);
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] select { color: #e2e8f0 !important; background: rgba(255,255,255,0.05) !important; }

/* ── KPI Cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 14px;
    margin-bottom: 14px;
}
.kpi-grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 14px;
}

.kpi-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 22px 20px 18px;
    position: relative;
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
    cursor: default;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.6;
}
.kpi-card:hover {
    transform: translateY(-4px);
    background: rgba(255,255,255,0.045);
    box-shadow: 0 24px 48px rgba(0,0,0,0.5), 0 0 40px var(--glow);
}
.kpi-icon {
    font-size: 1.3rem;
    margin-bottom: 14px;
    display: block;
    filter: drop-shadow(0 0 8px var(--accent));
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 6px;
    background: linear-gradient(135deg, #fff 0%, var(--accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.kpi-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #475569;
    margin-bottom: 8px;
}
.kpi-sub {
    font-size: 0.76rem;
    font-weight: 500;
}
.kpi-sub.up   { color: #22c55e; }
.kpi-sub.down { color: #ef4444; }
.kpi-sub.mid  { color: #64748b; }

/* Glow orb decoration */
.kpi-card .orb {
    position: absolute;
    width: 80px; height: 80px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.07;
    bottom: -20px; right: -20px;
    filter: blur(20px);
}

/* ── Section headers ── */
.section-hdr {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 28px 0 18px;
}
.section-hdr-text {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #475569;
    white-space: nowrap;
}
.section-hdr-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(109,40,217,0.35), transparent);
}

/* ── Chart wrapper ── */
.chart-wrap {
    background: rgba(255,255,255,0.018);
    border: 1px solid rgba(255,255,255,0.065);
    border-radius: 20px;
    padding: 20px 16px 12px;
    position: relative;
    overflow: hidden;
}
.chart-wrap::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(109,40,217,0.5), transparent);
}
.chart-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #475569;
    margin-bottom: 12px;
    padding-left: 4px;
}

/* ── Live badge ── */
.live-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.25);
    padding: 6px 14px;
    border-radius: 50px;
    font-size: 0.72rem;
    font-weight: 700;
    color: #22c55e;
    letter-spacing: 0.08em;
}
.live-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22c55e;
    animation: livePulse 2s ease-in-out infinite;
}
@keyframes livePulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.85); }
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(109,40,217,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(109,40,217,0.5) !important;
}

/* Inputs / selects */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

/* Sliders */
div[data-baseweb="slider"] div[role="slider"] { background: #7c3aed !important; }

/* Expander */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.018) !important;
    border: 1px solid rgba(255,255,255,0.065) !important;
    border-radius: 14px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(109,40,217,0.5); border-radius: 3px; }

/* Dataframe */
[data-testid="stDataFrame"] iframe { border-radius: 14px !important; }

/* Alert */
[data-testid="stAlert"] {
    background: rgba(109,40,217,0.08) !important;
    border: 1px solid rgba(109,40,217,0.3) !important;
    border-radius: 12px !important;
}

/* Divider */
hr { border: none !important; border-top: 1px solid rgba(255,255,255,0.05) !important; margin: 12px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#64748b", size=11),
    margin=dict(t=8, b=8, l=0, r=0),
    hovermode="x unified",
)

def section(label: str):
    st.markdown(f"""
    <div class="section-hdr">
        <span class="section-hdr-text">{label}</span>
        <div class="section-hdr-line"></div>
    </div>""", unsafe_allow_html=True)

def kpi(icon, label, value, sub="", sub_type="mid",
        accent="#7c3aed", glow="rgba(109,40,217,0.2)"):
    return f"""
    <div class="kpi-card" style="--accent:{accent};--glow:{glow};">
        <div class="orb"></div>
        <span class="kpi-icon">{icon}</span>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {"" if not sub else f'<div class="kpi-sub {sub_type}">{sub}</div>'}
    </div>"""

def chart_wrap(title: str, fig, height=320):
    st.markdown(f'<div class="chart-wrap"><div class="chart-title">{title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=title)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Data loaders ───────────────────────────────────────────────────────────────
SCOPES    = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
TOKEN_FILE = "token.json"
SHEET_NAME = "Sales Calls"

HEADERS_COLS = {
    "ts":         "Timestamp",
    "name":       "Name",
    "company":    "Company",
    "status":     "Call Status",
    "outcome":    "Outcome",
    "interested": "Interested",
    "pain":       "Pain Point",
    "duration":   "Duration (s)",
    "summary":    "Call Summary",
    "transcript": "Full Transcript",
    "meet":       "Google Meet Link",
}

OUTCOME_LABELS = {
    "booked_call": "Booked", "not_interested": "Not Interested",
    "follow_up_email": "Follow-up", "callback_requested": "Callback",
    "voicemail": "Voicemail", "unknown": "Unknown", "": "Pending",
}
OUTCOME_COLORS = {
    "Booked": "#22c55e", "Not Interested": "#ef4444",
    "Follow-up": "#f59e0b", "Callback": "#6366f1",
    "Voicemail": "#475569", "Unknown": "#334155", "Pending": "#1e293b",
}

@st.cache_data(ttl=60, show_spinner=False)
def load_sheet() -> pd.DataFrame:
    sheet_id  = os.getenv("GOOGLE_SHEET_ID", "")
    token_path = TOKEN_FILE

    if not os.path.exists(TOKEN_FILE) and hasattr(st, "secrets") and "google_token" in st.secrets:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(dict(st.secrets["google_token"]), tmp)
        tmp.close()
        token_path = tmp.name

    if not os.path.exists(token_path):
        return pd.DataFrame()

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        client = gspread.authorize(creds)
        ws = client.open_by_key(sheet_id).worksheet(SHEET_NAME)
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        ts_col = HEADERS_COLS["ts"]
        if ts_col in df.columns:
            df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
        dur_col = HEADERS_COLS["duration"]
        if dur_col in df.columns:
            df[dur_col] = pd.to_numeric(df[dur_col], errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"Sheet error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_vapi_spend(days: int) -> float:
    key = os.getenv("VAPI_API_KEY", "")
    if not key:
        return 0.0
    try:
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        total, page = 0.0, 1
        while True:
            r = requests.get(
                "https://api.vapi.ai/call",
                headers={"Authorization": f"Bearer {key}"},
                params={"limit": 100, "page": page, "createdAtGt": since},
                timeout=10,
            )
            if not r.ok: break
            calls = r.json()
            if not calls: break
            for c in calls:
                total += float(c.get("cost") or 0)
            if len(calls) < 100: break
            page += 1
        return round(total, 4)
    except Exception:
        return 0.0

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧪 Brew Labs Media")
    st.caption("Sales Agent Dashboard")
    st.divider()

    st.markdown("**⚙️ Configuration**")
    deal_value    = st.number_input("Avg deal value ($/mo)", 0, 100000, 2000, 100)
    cost_per_lead = st.number_input("Research cost / lead ($)", 0.0, 1.0, 0.01, 0.001, format="%.3f")

    st.divider()
    st.markdown("**📅 Period**")
    period = st.selectbox("", ["This month", "Last 30 days", "Last 7 days", "All time"], label_visibility="collapsed")

    st.divider()
    if st.button("⟳  Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"Auto-refresh · 60s\nLast: {datetime.now().strftime('%H:%M:%S')}")

# ── Date filtering ─────────────────────────────────────────────────────────────
now = datetime.now()
if   period == "This month":   start = now.replace(day=1,hour=0,minute=0,second=0,microsecond=0); days_back = max((now-start).days+1,1)
elif period == "Last 30 days": start = now - timedelta(days=30);  days_back = 30
elif period == "Last 7 days":  start = now - timedelta(days=7);   days_back = 7
else:                          start = datetime(2000,1,1);         days_back = 3650

# ── Load & filter ──────────────────────────────────────────────────────────────
with st.spinner(""):
    df_all = load_sheet()

ts_col = HEADERS_COLS["ts"]
df = df_all[df_all[ts_col] >= pd.Timestamp(start)].copy() if (not df_all.empty and ts_col in df_all.columns) else df_all.copy()
has_data = not df.empty

# ── KPI calculations ───────────────────────────────────────────────────────────
total_calls = len(df)
status_col  = HEADERS_COLS["status"]
outcome_col = HEADERS_COLS["outcome"]
dur_col     = HEADERS_COLS["duration"]

connected = int(df[status_col].str.lower().isin(["completed","ended"]).sum()) if has_data and status_col in df.columns else total_calls

bookings = follow_ups = callbacks = voicemails = not_int = 0
if has_data and outcome_col in df.columns:
    oc = df[outcome_col].str.lower().str.strip()
    bookings   = int((oc == "booked_call").sum())
    follow_ups = int((oc == "follow_up_email").sum())
    callbacks  = int((oc == "callback_requested").sum())
    voicemails = int((oc == "voicemail").sum())
    not_int    = int((oc == "not_interested").sum())

interested  = bookings + follow_ups + callbacks
answer_rate = (connected / total_calls * 100) if total_calls else 0
conv_rate   = (bookings / connected * 100) if connected else 0
avg_dur     = df[dur_col].mean() if has_data and dur_col in df.columns else 0

vapi_spend     = load_vapi_spend(days_back)
research_spend = round(total_calls * cost_per_lead, 2)
total_cost     = round(vapi_spend + research_spend, 2)
revenue        = bookings * deal_value
profit         = revenue - total_cost
roi            = ((profit / total_cost) * 100) if total_cost else 0
cpb            = (total_cost / bookings) if bookings else 0

# ── HEADER ────────────────────────────────────────────────────────────────────
if True:
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0 24px;">
        <div>
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">
                <span style="font-size:2.2rem;">🧪</span>
                <span style="font-size:2rem;font-weight:900;letter-spacing:-0.04em;
                    background:linear-gradient(135deg,#fff 0%,#c4b5fd 45%,#67e8f9 100%);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                    Brew Labs Media
                </span>
            </div>
            <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.2em;color:#334155;margin-left:3.4rem;">
                OUTBOUND SALES INTELLIGENCE
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="text-align:right;">
                <div style="font-size:0.68rem;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.08em;">Period</div>
                <div style="font-size:0.88rem;font-weight:700;color:#e2e8f0;">{period}</div>
            </div>
            <div class="live-badge">
                <div class="live-dot"></div> LIVE
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── CALL PERFORMANCE ──────────────────────────────────────────────────────────
section("📞 &nbsp; Call Performance")

st.markdown(
    '<div class="kpi-grid">' +
    kpi("📤", "Calls Made",     f"{total_calls:,}",
        sub=f"period total", sub_type="mid",
        accent="#7c3aed", glow="rgba(124,58,237,0.2)") +
    kpi("📲", "Connected",      f"{connected:,}",
        sub=f"{answer_rate:.0f}% answer rate", sub_type="up" if answer_rate>30 else "mid",
        accent="#06b6d4", glow="rgba(6,182,212,0.2)") +
    kpi("🗓️", "Bookings",       f"{bookings:,}",
        sub="discovery calls", sub_type="up" if bookings>0 else "mid",
        accent="#22c55e", glow="rgba(34,197,94,0.2)") +
    kpi("🎯", "Conversion",     f"{conv_rate:.1f}%",
        sub="booked ÷ connected", sub_type="up" if conv_rate>5 else "mid",
        accent="#f59e0b", glow="rgba(245,158,11,0.2)") +
    kpi("📧", "Follow-ups",     f"{follow_ups:,}",
        sub="email requested", sub_type="mid",
        accent="#6366f1", glow="rgba(99,102,241,0.2)") +
    kpi("⏱️", "Avg Duration",   f"{avg_dur:.0f}s" if avg_dur else "—",
        sub="per call", sub_type="mid",
        accent="#8b5cf6", glow="rgba(139,92,246,0.2)") +
    '</div>',
    unsafe_allow_html=True,
)

# ── FINANCIALS ────────────────────────────────────────────────────────────────
section("💰 &nbsp; Financials")

roi_color = "#22c55e" if roi >= 0 else "#ef4444"
roi_glow  = "rgba(34,197,94,0.2)" if roi >= 0 else "rgba(239,68,68,0.2)"

st.markdown(
    '<div class="kpi-grid">' +
    kpi("🔌", "Vapi Spend",     f"${vapi_spend:.2f}",
        sub="live from Vapi API", sub_type="mid",
        accent="#64748b", glow="rgba(100,116,139,0.15)") +
    kpi("🧠", "Research Spend", f"${research_spend:.2f}",
        sub=f"{total_calls} leads × ${cost_per_lead:.3f}", sub_type="mid",
        accent="#6366f1", glow="rgba(99,102,241,0.15)") +
    kpi("💸", "Total Cost",     f"${total_cost:.2f}",
        sub="all APIs combined", sub_type="mid",
        accent="#ef4444", glow="rgba(239,68,68,0.15)") +
    kpi("💵", "Revenue",        f"${revenue:,.0f}",
        sub=f"{bookings} × ${deal_value:,}/mo", sub_type="up" if revenue>0 else "mid",
        accent="#22c55e", glow="rgba(34,197,94,0.2)") +
    kpi("📈", "Net Profit",     f"${profit:,.0f}",
        sub="revenue − cost", sub_type="up" if profit>=0 else "down",
        accent="#10b981" if profit>=0 else "#ef4444",
        glow="rgba(16,185,129,0.2)" if profit>=0 else "rgba(239,68,68,0.2)") +
    kpi("🚀", "ROI",            f"{roi:.0f}%",
        sub="return on spend", sub_type="up" if roi>=0 else "down",
        accent=roi_color, glow=roi_glow) +
    '</div>',
    unsafe_allow_html=True,
)

if bookings > 0:
    st.markdown(f"""
    <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);
                border-radius:12px;padding:12px 18px;margin:4px 0 0;
                font-size:0.82rem;color:#86efac;font-weight:500;">
        💡 &nbsp; Cost per booking: <strong style="color:#4ade80;">${cpb:.2f}</strong>
        &nbsp;·&nbsp; You spent <strong style="color:#4ade80;">${total_cost:.2f}</strong> to generate
        <strong style="color:#4ade80;">${revenue:,.0f}</strong> in revenue this period.
    </div>""", unsafe_allow_html=True)

# ── CHARTS ROW 1 ──────────────────────────────────────────────────────────────
section("📊 &nbsp; Analytics")
col_big, col_sm = st.columns([3, 2])

with col_big:
    if has_data and ts_col in df.columns:
        daily = (df.dropna(subset=[ts_col])
                   .groupby(df[ts_col].dt.strftime("%Y-%m-%d")).size()
                   .reset_index(name="Calls")
                   .rename(columns={ts_col: "Date"}))
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily["Date"], y=daily["Calls"],
            mode="lines+markers",
            fill="tozeroy",
            fillcolor="rgba(109,40,217,0.12)",
            line=dict(color="#7c3aed", width=2.5),
            marker=dict(size=7, color="#7c3aed",
                        line=dict(color="#c4b5fd", width=1.5)),
            hovertemplate="<b>%{x}</b><br>%{y} calls<extra></extra>",
        ))
        fig.update_layout(**PLOT_LAYOUT, height=300,
            xaxis=dict(showgrid=False, color="#334155"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color="#334155"),
        )
        chart_wrap("Calls Over Time", fig)
    else:
        st.markdown('<div class="chart-wrap" style="height:300px;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.85rem;">No call data yet</div>', unsafe_allow_html=True)

with col_sm:
    if has_data and outcome_col in df.columns and total_calls > 0:
        oc_counts = (df[outcome_col].str.lower().str.strip().value_counts().reset_index())
        oc_counts.columns = ["outcome", "count"]
        oc_counts["label"] = oc_counts["outcome"].map(lambda x: OUTCOME_LABELS.get(x, x.title()))
        oc_counts["color"] = oc_counts["label"].map(lambda x: OUTCOME_COLORS.get(x, "#334155"))
        fig2 = go.Figure(go.Pie(
            labels=oc_counts["label"],
            values=oc_counts["count"],
            hole=0.55,
            marker=dict(colors=oc_counts["color"].tolist(),
                        line=dict(color="#03020d", width=3)),
            textinfo="percent",
            hovertemplate="<b>%{label}</b><br>%{value} calls (%{percent})<extra></extra>",
        ))
        fig2.add_annotation(
            text=f"<b>{total_calls}</b><br><span style='font-size:10px'>calls</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="#e2e8f0", size=18),
        )
        fig2.update_layout(**PLOT_LAYOUT, height=300, showlegend=True,
            legend=dict(orientation="v", x=1, y=0.5, font=dict(color="#64748b", size=11)),
        )
        chart_wrap("Outcome Breakdown", fig2)
    else:
        st.markdown('<div class="chart-wrap" style="height:300px;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.85rem;">No outcome data yet</div>', unsafe_allow_html=True)

# ── CHARTS ROW 2 ──────────────────────────────────────────────────────────────
col_f, col_r = st.columns(2)

with col_f:
    fig3 = go.Figure(go.Funnel(
        y=["Calls Made", "Connected", "Interested", "Booked"],
        x=[total_calls, connected, interested, bookings],
        textinfo="value+percent initial",
        textfont=dict(color="#fff", size=12, family="Inter"),
        marker=dict(
            color=["#7c3aed", "#6366f1", "#06b6d4", "#22c55e"],
            line=dict(color="#03020d", width=2),
        ),
        connector=dict(line=dict(color="rgba(255,255,255,0.04)", width=1)),
        hovertemplate="<b>%{label}</b><br>%{value} (%{percentInitial})<extra></extra>",
    ))
    fig3.update_layout(**PLOT_LAYOUT, height=280, showlegend=False,
        yaxis=dict(color="#475569"),
    )
    chart_wrap("Conversion Funnel", fig3)

with col_r:
    categories = ["Revenue", "Vapi Spend", "Research Spend"]
    values     = [revenue, vapi_spend, research_spend]
    colors     = ["#22c55e", "#ef4444", "#f59e0b"]
    fig4 = go.Figure(go.Bar(
        x=categories, y=values,
        marker=dict(
            color=[f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.85)" for c in colors],
            line=dict(color=colors, width=1.5),
            cornerradius=8,
        ),
        text=[f"${v:,.2f}" for v in values],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    fig4.update_layout(**PLOT_LAYOUT, height=280,
        xaxis=dict(showgrid=False, color="#475569"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color="#475569"),
    )
    chart_wrap("Revenue vs Cost", fig4)

# ── ROI PROJECTOR ─────────────────────────────────────────────────────────────
section("🔮 &nbsp; ROI Projector")

st.markdown("""
<div style="background:rgba(109,40,217,0.06);border:1px solid rgba(109,40,217,0.2);
            border-radius:16px;padding:24px 28px;">
""", unsafe_allow_html=True)

s1, s2, s3 = st.columns(3)
with s1: proj_calls  = st.slider("Calls / month",    10, 500,  max(total_calls or 50, 50),  10)
with s2: proj_answer = st.slider("Answer rate (%)",   5,  80,  max(int(answer_rate or 30), 5))
with s3: proj_conv   = st.slider("Booking rate (%)", 1,  40,  max(int(conv_rate or 5), 1))

proj_connected = int(proj_calls * proj_answer / 100)
proj_bookings  = int(proj_connected * proj_conv / 100)
proj_revenue   = proj_bookings * deal_value
proj_vapi      = proj_calls * (vapi_spend / total_calls if total_calls else 0.08)
proj_cost      = round(proj_vapi + proj_calls * cost_per_lead, 2)
proj_profit    = proj_revenue - proj_cost
proj_roi       = ((proj_profit / proj_cost) * 100) if proj_cost else 0

st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

p1, p2, p3, p4 = st.columns(4)
for col, icon, label, value, sub, stype, acc, glow in [
    (p1, "📲", "Proj. Connected",  f"{proj_connected:,}",    f"{proj_answer}% of {proj_calls}", "mid",  "#06b6d4", "rgba(6,182,212,0.2)"),
    (p2, "🗓️", "Proj. Bookings",   f"{proj_bookings:,}",     f"{proj_conv}% conv. rate",        "up",   "#22c55e", "rgba(34,197,94,0.2)"),
    (p3, "💵", "Proj. Revenue",    f"${proj_revenue:,.0f}",  f"{proj_bookings} × ${deal_value:,}", "up" if proj_revenue>0 else "mid", "#f59e0b", "rgba(245,158,11,0.2)"),
    (p4, "🚀", "Proj. ROI",        f"{proj_roi:.0f}%",       f"net ${proj_profit:,.0f}",         "up" if proj_roi>=0 else "down",
     "#22c55e" if proj_roi>=0 else "#ef4444",
     "rgba(34,197,94,0.2)" if proj_roi>=0 else "rgba(239,68,68,0.2)"),
]:
    with col:
        st.markdown('<div class="kpi-grid-4">' if False else "", unsafe_allow_html=True)
        st.markdown(kpi(icon, label, value, sub, stype, acc, glow), unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── RECENT CALLS ──────────────────────────────────────────────────────────────
section("📋 &nbsp; Recent Calls")

if has_data:
    SHOW_COLS = [HEADERS_COLS[k] for k in ["ts","name","company","status","outcome","interested","pain","duration","meet"] if HEADERS_COLS[k] in df.columns]
    df_disp = df.sort_values(ts_col, ascending=False).head(30)[SHOW_COLS].copy()
    if ts_col in df_disp.columns:
        df_disp[ts_col] = df_disp[ts_col].dt.strftime("%d %b %Y  %H:%M")
    oc = HEADERS_COLS["outcome"]
    if oc in df_disp.columns:
        df_disp[oc] = df_disp[oc].map(lambda x: OUTCOME_LABELS.get(str(x).lower().strip(), x))

    st.dataframe(
        df_disp,
        use_container_width=True,
        hide_index=True,
        column_config={
            HEADERS_COLS["meet"]:     st.column_config.LinkColumn("Meet Link"),
            HEADERS_COLS["duration"]: st.column_config.NumberColumn("Duration", format="%d s"),
            HEADERS_COLS["ts"]:       st.column_config.TextColumn("Time"),
        },
    )

    with st.expander("🔍  View full transcript"):
        tr_col = HEADERS_COLS["transcript"]
        if tr_col in df.columns:
            opts = df.sort_values(ts_col, ascending=False).head(20)
            sel  = st.selectbox(
                "Pick a call",
                opts.index,
                format_func=lambda i: (
                    f"{df.loc[i, HEADERS_COLS['name']]}  ·  "
                    f"{df.loc[i, ts_col].strftime('%d %b %Y %H:%M') if pd.notna(df.loc[i, ts_col]) else '—'}"
                    if HEADERS_COLS["name"] in df.columns else str(i)
                ),
            )
            if sel is not None:
                row = df.loc[sel]
                summ = row.get(HEADERS_COLS["summary"], "")
                if summ:
                    st.markdown(f"""
                    <div style="background:rgba(109,40,217,0.08);border:1px solid rgba(109,40,217,0.2);
                                border-radius:10px;padding:14px 18px;margin-bottom:12px;
                                font-size:0.84rem;color:#c4b5fd;line-height:1.6;">
                        <strong style="color:#a78bfa;font-size:0.7rem;letter-spacing:0.08em;text-transform:uppercase;">Summary</strong><br>{summ}
                    </div>""", unsafe_allow_html=True)
                st.text_area("Full Transcript", value=row.get(tr_col, "No transcript available"), height=280)
else:
    st.markdown("""
    <div style="text-align:center;padding:60px 0;color:#334155;font-size:0.9rem;">
        No calls logged yet · Run <code style="color:#7c3aed;">python3 run_calls.py</code> to get started
    </div>""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.05);
            display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:0.7rem;color:#1e293b;font-weight:600;letter-spacing:0.06em;">
        BREW LABS MEDIA · OUTBOUND SALES AGENT
    </span>
    <span style="font-size:0.7rem;color:#1e293b;">
        Data refreshes every 60s · Built with Streamlit
    </span>
</div>
""", unsafe_allow_html=True)
