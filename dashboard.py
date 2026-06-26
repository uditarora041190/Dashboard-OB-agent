"""
dashboard.py  —  Brew Labs Media · Outbound Sales Dashboard
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

# ── THEME ─────────────────────────────────────────────────────────────────────
ORANGE  = "#FF4D1C"
ORANGE2 = "#FF6B35"
BLACK   = "#000000"
GREY1   = "#0D0D0D"
GREY2   = "#141414"
GREY3   = "#1C1C1C"
BORDER  = "#2A2A2A"
WHITE   = "#FFFFFF"
MUTED   = "#555555"
TEXT2   = "#999999"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background: {BLACK} !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: {WHITE} !important;
}}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stDeployButton {{ visibility: hidden !important; height: 0 !important; }}

/* Main container */
.main .block-container {{
    padding: 0 2.5rem 4rem !important;
    max-width: 100% !important;
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: {GREY1} !important;
    border-right: 1px solid {BORDER} !important;
}}
section[data-testid="stSidebar"] * {{ color: {WHITE} !important; }}
section[data-testid="stSidebar"] input {{
    background: {GREY2} !important;
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

.kpi-card {{
    background: {GREY1};
    padding: 28px 24px 22px;
    position: relative;
    overflow: hidden;
    transition: background 0.2s ease;
}}
.kpi-card:hover {{
    background: {GREY2};
}}
.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent, {BORDER});
    transition: opacity 0.2s;
}}
.kpi-card:hover::before {{
    opacity: 1;
    background: {ORANGE};
}}
.kpi-label {{
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: {MUTED};
    margin-bottom: 10px;
}}
.kpi-value {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    line-height: 1;
    letter-spacing: 0.02em;
    color: {WHITE};
    margin-bottom: 6px;
}}
.kpi-value.orange {{ color: {ORANGE}; }}
.kpi-sub {{
    font-size: 0.72rem;
    font-weight: 500;
    color: {TEXT2};
}}
.kpi-sub.up   {{ color: #22c55e; }}
.kpi-sub.down {{ color: #ef4444; }}

/* ── Section headers ── */
.section-hdr {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 32px 0 20px;
}}
.section-hdr-label {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.15em;
    color: {MUTED};
    white-space: nowrap;
}}
.section-hdr-line {{
    flex: 1;
    height: 1px;
    background: {BORDER};
}}

/* ── Chart wrapper ── */
.chart-box {{
    background: {GREY1};
    border: 1px solid {BORDER};
    padding: 24px 20px 16px;
    position: relative;
}}
.chart-box-title {{
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: {MUTED};
    margin-bottom: 16px;
}}

/* ── Topbar ── */
.topbar {{
    background: {BLACK};
    border-bottom: 1px solid {BORDER};
    padding: 0 0 0;
    margin: 0 -2.5rem 0;
    display: flex;
    align-items: stretch;
}}
.topbar-logo {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 20px 32px;
    border-right: 1px solid {BORDER};
}}
.logo-box {{
    width: 40px; height: 40px;
    background: {ORANGE};
    display: flex; align-items: center; justify-content: center;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    color: {WHITE};
    flex-shrink: 0;
}}
.logo-text {{
    display: flex; flex-direction: column; gap: 0;
}}
.logo-text-top {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem;
    letter-spacing: 0.12em;
    color: {WHITE};
    line-height: 1;
}}
.logo-text-bot {{
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    color: {MUTED};
    text-transform: uppercase;
}}
.topbar-center {{
    flex: 1;
    display: flex;
    align-items: center;
    padding: 0 32px;
}}
.topbar-title {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.2em;
    color: {MUTED};
}}
.topbar-right {{
    display: flex;
    align-items: center;
    gap: 0;
    border-left: 1px solid {BORDER};
}}
.topbar-stat {{
    padding: 0 28px;
    border-right: 1px solid {BORDER};
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 3px;
}}
.topbar-stat-val {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    letter-spacing: 0.04em;
    color: {WHITE};
    line-height: 1;
}}
.topbar-stat-val.orange {{ color: {ORANGE}; }}
.topbar-stat-label {{
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {MUTED};
}}
.live-pill {{
    padding: 0 24px;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.live-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #22c55e;
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%,100% {{ opacity:1; }} 50% {{ opacity:0.3; }}
}}
.live-text {{
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.2em;
    color: #22c55e;
}}

/* ── Insight bar ── */
.insight-bar {{
    background: {ORANGE};
    padding: 12px 24px;
    margin: 0 -2.5rem;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: {WHITE};
}}

/* ── Buttons ── */
.stButton > button {{
    background: {ORANGE} !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: 0 !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    transition: background 0.15s !important;
}}
.stButton > button:hover {{
    background: {ORANGE2} !important;
}}

/* Inputs */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input {{
    background: {GREY2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 0 !important;
    color: {WHITE} !important;
}}

/* Slider */
div[data-baseweb="slider"] div[role="slider"] {{ background: {ORANGE} !important; }}
[data-testid="stSlider"] [class*="Track"] [class*="Inner"] {{ background: {ORANGE} !important; }}

/* Expander */
[data-testid="stExpander"] {{
    background: {GREY1} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 0 !important;
}}

/* Table */
[data-testid="stDataFrame"] iframe {{ border-radius: 0 !important; }}

/* Alert */
[data-testid="stAlert"] {{
    background: rgba(255,61,0,0.08) !important;
    border: 1px solid rgba(255,61,0,0.3) !important;
    border-radius: 0 !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: {BLACK}; }}
::-webkit-scrollbar-thumb {{ background: {ORANGE}; }}

/* Divider */
hr {{ border: none !important; border-top: 1px solid {BORDER} !important; margin: 0 !important; }}
</style>
""", unsafe_allow_html=True)

# ── Chart layout defaults ──────────────────────────────────────────────────────
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
        <span class="section-hdr-label">{label}</span>
        <div class="section-hdr-line"></div>
    </div>""", unsafe_allow_html=True)

def chart_box(title, fig, height=300):
    st.markdown(f'<div class="chart-box"><div class="chart-box-title">{title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=title)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
TOKEN_FILE = "token.json"
SHEET_NAME = "Sales Calls"
C = {
    "ts": "Timestamp", "name": "Name", "company": "Company",
    "status": "Call Status", "outcome": "Outcome", "interested": "Interested",
    "pain": "Pain Point", "duration": "Duration (s)",
    "summary": "Call Summary", "transcript": "Full Transcript",
    "meet": "Google Meet Link",
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
    # Render.com: load token from environment variable
    if not os.path.exists(TOKEN_FILE) and os.getenv("GOOGLE_TOKEN_JSON"):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(os.getenv("GOOGLE_TOKEN_JSON")); tmp.close()
        token_path = tmp.name
    # Streamlit Cloud: load token from secrets
    elif not os.path.exists(TOKEN_FILE) and hasattr(st, "secrets") and "google_token" in st.secrets:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(dict(st.secrets["google_token"]), tmp); tmp.close()
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
        return df
    except Exception as e:
        st.error(f"Sheet error: {e}")
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

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.2rem;letter-spacing:0.1em;color:{ORANGE};margin-bottom:4px;'>Settings</div>", unsafe_allow_html=True)
    deal_value    = st.number_input("Avg deal value ($/mo)", 0, 100000, 2000, 100)
    cost_per_lead = st.number_input("Research cost/lead ($)", 0.0, 1.0, 0.01, 0.001, format="%.3f")
    st.divider()
    st.markdown(f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.2rem;letter-spacing:0.1em;color:{ORANGE};margin-bottom:4px;'>Period</div>", unsafe_allow_html=True)
    period = st.selectbox("", ["This month","Last 30 days","Last 7 days","All time"], label_visibility="collapsed")
    st.divider()
    if st.button("↺  REFRESH", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown(f"<div style='font-size:0.65rem;color:{MUTED};margin-top:12px;'>Auto-refresh · 60s<br>Last: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# ── Date filter ────────────────────────────────────────────────────────────────
now = datetime.now()
if   period == "This month":   start = now.replace(day=1,hour=0,minute=0,second=0,microsecond=0); days_back = max((now-start).days+1,1)
elif period == "Last 30 days": start = now - timedelta(days=30);  days_back = 30
elif period == "Last 7 days":  start = now - timedelta(days=7);   days_back = 7
else:                          start = datetime(2000,1,1);         days_back = 3650

with st.spinner(""):
    df_all = load_sheet()

df = df_all[df_all[C["ts"]] >= pd.Timestamp(start)].copy() if (not df_all.empty and C["ts"] in df_all.columns) else df_all.copy()
has = not df.empty

# ── KPIs ──────────────────────────────────────────────────────────────────────
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

# ── TOP BAR ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar">
    <div class="topbar-logo">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="40" height="40" style="flex-shrink:0;">
          <rect width="64" height="64" fill="#FF4D1C"/>
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
        <span class="topbar-title">Outbound Sales Dashboard</span>
    </div>
    <div class="topbar-right">
        <div class="topbar-stat">
            <div class="topbar-stat-val orange">{bookings}</div>
            <div class="topbar-stat-label">Bookings</div>
        </div>
        <div class="topbar-stat">
            <div class="topbar-stat-val">{answer_rate:.0f}%</div>
            <div class="topbar-stat-label">Answer Rate</div>
        </div>
        <div class="topbar-stat">
            <div class="topbar-stat-val orange">${revenue:,.0f}</div>
            <div class="topbar-stat-label">Revenue</div>
        </div>
        <div class="live-pill">
            <div class="live-dot"></div>
            <span class="live-text">LIVE</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Insight bar
if bookings > 0:
    st.markdown(f'<div class="insight-bar">[ PERFORMANCE ] &nbsp; Cost per booking: <strong>${cpb:.2f}</strong> &nbsp;·&nbsp; {bookings} bookings × ${deal_value:,}/mo = <strong>${revenue:,.0f}</strong> pipeline &nbsp;·&nbsp; ROI: <strong>{roi:.0f}%</strong></div>', unsafe_allow_html=True)

# ── CALL PERFORMANCE ──────────────────────────────────────────────────────────
section("01 / Call Performance")

def kpi(label, value, sub="", orange=False, sub_type=""):
    oc = "orange" if orange else ""
    sc = f' {sub_type}' if sub_type else ""
    return f"""<div class="kpi-card"><div class="kpi-label">{label}</div>
    <div class="kpi-value {oc}">{value}</div>
    {"" if not sub else f'<div class="kpi-sub{sc}">{sub}</div>'}
    </div>"""

st.markdown(
    '<div class="kpi-row kpi-row-6">' +
    kpi("Calls Made",     f"{total:,}",           f"period total") +
    kpi("Connected",      f"{connected:,}",         f"{answer_rate:.0f}% answer rate", sub_type="up" if answer_rate>30 else "") +
    kpi("Bookings",       f"{bookings:,}",           "discovery calls", orange=True) +
    kpi("Conversion",     f"{conv_rate:.1f}%",       "booked ÷ connected", sub_type="up" if conv_rate>5 else "") +
    kpi("Follow-ups",     f"{follow_ups:,}",         "email requested") +
    kpi("Avg Duration",   f"{avg_dur:.0f}s" if avg_dur else "—", "per call") +
    '</div>',
    unsafe_allow_html=True,
)

# ── FINANCIALS ────────────────────────────────────────────────────────────────
section("02 / Financials")

st.markdown(
    '<div class="kpi-row kpi-row-6">' +
    kpi("Vapi Spend",     f"${api_spend:.2f}",       "live from API") +
    kpi("Research Spend", f"${research_spend:.2f}",  f"{total} leads") +
    kpi("Total Cost",     f"${total_cost:.2f}",       "all APIs", sub_type="down" if total_cost>0 else "") +
    kpi("Revenue",        f"${revenue:,.0f}",         f"{bookings} × ${deal_value:,}", orange=True, sub_type="up" if revenue>0 else "") +
    kpi("Net Profit",     f"${profit:,.0f}",          "revenue − cost", sub_type="up" if profit>=0 else "down") +
    kpi("ROI",            f"{roi:.0f}%",              "return on spend", orange=roi>=0, sub_type="up" if roi>=0 else "down") +
    '</div>',
    unsafe_allow_html=True,
)

# ── CHARTS ────────────────────────────────────────────────────────────────────
section("03 / Analytics")

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
            marker=dict(color=ORANGE, opacity=0.9, line=dict(color=ORANGE2, width=0)),
            hovertemplate="<b>%{x}</b><br>%{y} calls<extra></extra>",
        ))
        # Add line on top
        fig.add_trace(go.Scatter(
            x=daily["Date"], y=daily["Calls"],
            mode="lines", line=dict(color=WHITE, width=1.5, dash="dot"),
            hoverinfo="skip",
        ))
        fig.update_layout(**plot_layout(height=300,
            xaxis=dict(showgrid=False, color=MUTED, linecolor=BORDER),
            yaxis=dict(showgrid=True, gridcolor=GREY3, color=MUTED, linecolor=BORDER),
        ))
        chart_box("Calls Over Time", fig)
    else:
        st.markdown(f'<div class="chart-box" style="height:300px;display:flex;align-items:center;justify-content:center;color:{MUTED};font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;">No Data Yet</div>', unsafe_allow_html=True)

with col2:
    if has and C["outcome"] in df.columns and total > 0:
        oc_cnt = df[C["outcome"]].str.lower().str.strip().value_counts().reset_index()
        oc_cnt.columns = ["outcome","count"]
        oc_cnt["label"] = oc_cnt["outcome"].map(lambda x: OUTCOME_MAP.get(x, x.title()))
        colors = [ORANGE if l=="Booked" else GREY3 if l in ["Not Interested","Pending"] else "#FF6B35" if l=="Follow-up" else "#666" for l in oc_cnt["label"]]
        fig2 = go.Figure(go.Pie(
            labels=oc_cnt["label"], values=oc_cnt["count"],
            hole=0.6,
            marker=dict(colors=colors, line=dict(color=BLACK, width=3)),
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
        st.markdown(f'<div class="chart-box" style="height:300px;display:flex;align-items:center;justify-content:center;color:{MUTED};font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;">No Data Yet</div>', unsafe_allow_html=True)

# Row 2
c3, c4 = st.columns(2)
with c3:
    stages = ["Calls Made","Connected","Interested","Booked"]
    vals   = [total, connected, interested, bookings]
    fig3 = go.Figure(go.Funnel(
        y=stages, x=vals,
        textinfo="value+percent initial",
        textfont=dict(color=WHITE, size=12, family="Inter"),
        marker=dict(
            color=[GREY3, GREY2, "#FF6B35", ORANGE],
            line=dict(color=BLACK, width=2),
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
    bar_colors = [ORANGE, GREY3, GREY2]
    fig4 = go.Figure(go.Bar(
        x=categories, y=values,
        marker=dict(color=bar_colors, line=dict(color=[ORANGE2,"#333","#2a2a2a"], width=1)),
        text=[f"${v:,.2f}" for v in values],
        textposition="outside",
        textfont=dict(color=TEXT2, size=11),
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    fig4.update_layout(**plot_layout(height=280,
        yaxis=dict(showgrid=True, gridcolor=GREY3, color=MUTED),
    ))
    chart_box("Revenue vs Cost", fig4)

# ── ROI PROJECTOR ─────────────────────────────────────────────────────────────
section("04 / ROI Projector")

st.markdown(f'<div style="background:{GREY1};border:1px solid {BORDER};padding:24px 28px 28px;">', unsafe_allow_html=True)
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
    kpi("Proj. Connected",  f"{p_conn:,}",          f"{pa}% of {pc} calls") +
    kpi("Proj. Bookings",   f"{p_book:,}",           f"{pv}% conversion", orange=True) +
    kpi("Proj. Revenue",    f"${p_rev:,.0f}",        f"{p_book} × ${deal_value:,}", orange=True) +
    kpi("Proj. ROI",        f"{p_roi:.0f}%",         f"net ${p_rev-p_cost:,.0f}", orange=p_roi>=0, sub_type="up" if p_roi>=0 else "down") +
    '</div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# ── RECENT CALLS ──────────────────────────────────────────────────────────────
section("05 / Recent Calls")

if has:
    show = [C[k] for k in ["ts","name","company","status","outcome","interested","pain","duration","meet"] if C[k] in df.columns]
    disp = df.sort_values(C["ts"], ascending=False).head(30)[show].copy()
    if C["ts"] in disp.columns:
        disp[C["ts"]] = disp[C["ts"]].dt.strftime("%d %b %Y  %H:%M")
    if C["outcome"] in disp.columns:
        disp[C["outcome"]] = disp[C["outcome"]].map(lambda x: OUTCOME_MAP.get(str(x).lower().strip(), x))

    st.dataframe(disp, use_container_width=True, hide_index=True,
        column_config={
            C["meet"]:     st.column_config.LinkColumn("Meet Link"),
            C["duration"]: st.column_config.NumberColumn("Duration", format="%d s"),
            C["ts"]:       st.column_config.TextColumn("Time"),
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
                    st.markdown(f'<div style="background:{GREY2};border-left:3px solid {ORANGE};padding:14px 18px;margin-bottom:12px;font-size:0.83rem;color:{TEXT2};line-height:1.6;"><strong style="color:{ORANGE};font-size:0.62rem;letter-spacing:0.1em;text-transform:uppercase;display:block;margin-bottom:6px;">Summary</strong>{row.get(C["summary"],"")}</div>', unsafe_allow_html=True)
                st.text_area("Full Transcript", value=row.get(C["transcript"],"No transcript"), height=280)
else:
    st.markdown(f'<div style="padding:60px 0;text-align:center;color:{MUTED};font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;">No calls logged yet · Run python3 run_calls.py to begin</div>', unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:64px;border-top:1px solid {BORDER};padding-top:20px;
    display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:10px;">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="20" height="20"><rect width="64" height="64" fill="#FF4D1C"/><g fill="none" stroke="#000" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12v16a10 10 0 0 0 20 0V12"/><path d="M17 52h30"/><path d="M27 36c-5 3 -7 7 -7 14"/><path d="M37 36c5 3 7 7 7 14"/></g></svg>
        <span style="font-size:0.62rem;font-weight:700;letter-spacing:0.15em;color:{MUTED};text-transform:uppercase;">Brew Labs Media · Sales Intelligence</span>
    </div>
    <span style="font-size:0.62rem;color:{BORDER};letter-spacing:0.08em;">Data refreshes every 60s</span>
</div>
""", unsafe_allow_html=True)
