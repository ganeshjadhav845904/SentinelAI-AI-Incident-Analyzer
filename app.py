import os
import re
import sqlite3
from io import BytesIO
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# =========================================================
# SENTINELAI | ENTERPRISE INCIDENT INTELLIGENCE
# Existing SQLite schema and Gemini integration preserved.
# =========================================================

st.set_page_config(
    page_title="SentinelAI | Operations Control Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "SentinelAI"
DB_NAME = "sentinelai.db"
GEMINI_MODEL = "gemini-3.5-flash-lite"
SEVERITIES = ["Critical", "High", "Medium", "Low"]
STATUSES = ["Open", "In Progress", "Escalated", "Resolved", "Closed"]
TEAMS = ["L1 Operations", "L2 Application Support", "L3 Engineering", "DevOps & Cloud"]

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        gemini_client = None

# ------------------------------ DATABASE ------------------------------
def get_database_connection():
    return sqlite3.connect(DB_NAME)

def initialize_database():
    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT NOT NULL,
                assigned_team TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

def load_incidents(order="DESC"):
    order = "ASC" if str(order).upper() == "ASC" else "DESC"
    with get_database_connection() as connection:
        return pd.read_sql_query(
            f"SELECT * FROM incidents ORDER BY id {order}", connection
        )

initialize_database()

# ------------------------------ DESIGN SYSTEM ------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
      --bg:#07111f; --surface:#0d1b2d; --surface2:#11243a;
      --surface3:#162c45; --border:rgba(148,181,214,.15);
      --text:#edf6ff; --muted:#91a8c2; --cyan:#36d9ee;
      --blue:#579bff; --green:#37d6a0; --amber:#f6bd60;
      --red:#ff647c; --purple:#a78bfa;
    }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp {
      background:
        radial-gradient(ellipse at 78% -10%, rgba(25,130,170,.19), transparent 35%),
        radial-gradient(ellipse at 4% 35%, rgba(39,91,155,.12), transparent 30%),
        linear-gradient(145deg,#06101d 0%,#091626 52%,#07111f 100%);
      color:var(--text);
    }
    [data-testid="stHeader"] { background:rgba(5,14,26,.82); }
    [data-testid="stToolbar"] { right:1rem; }
    .block-container { max-width:1580px; padding-top:1.25rem; padding-bottom:3rem; }
    [data-testid="stSidebar"] {
      background:linear-gradient(180deg,#091729 0%,#0b1b2e 60%,#0a1728 100%);
      border-right:1px solid var(--border);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top:1.15rem; }
    [data-testid="stSidebar"] * { color:#dcecff; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
      padding: .42rem .55rem; border-radius:9px; font-weight:600;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
      background:rgba(54,217,238,.08);
    }
    h1,h2,h3,h4 { color:var(--text)!important; font-family:'Space Grotesk',sans-serif!important; letter-spacing:-.035em; }
    p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color:#b6c8dc; }
    .brand-lockup { display:flex; align-items:center; gap:11px; padding:7px 3px 15px; }
    .brand-mark {
      width:43px;height:43px;border-radius:13px;display:flex;align-items:center;justify-content:center;
      background:linear-gradient(145deg,rgba(54,217,238,.22),rgba(87,155,255,.16));
      border:1px solid rgba(54,217,238,.35);font-size:22px;box-shadow:0 0 28px rgba(54,217,238,.10);
    }
    .brand-name { font:700 22px 'Space Grotesk',sans-serif;color:#f4f9ff;letter-spacing:-.8px; }
    .brand-tag { font-size:9px;letter-spacing:1.8px;color:#70ddeb;font-weight:800;margin-top:1px; }
    .side-status { display:flex;align-items:center;gap:8px;background:rgba(55,214,160,.08);
      border:1px solid rgba(55,214,160,.18);border-radius:10px;padding:10px 11px;margin:10px 0 6px; }
    .pulse { width:7px;height:7px;background:#37d6a0;border-radius:50%;box-shadow:0 0 10px #37d6a0; }
    .side-small { color:#718aa6;font-size:10px;letter-spacing:.7px;text-transform:uppercase;font-weight:700; }
    .topline { display:flex;justify-content:space-between;align-items:center;gap:12px;margin:2px 0 18px; }
    .eyebrow { color:#55d9e9;font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase; }
    .page-title { font:700 30px 'Space Grotesk',sans-serif;color:#f4f8ff;letter-spacing:-1.1px;margin:4px 0 2px; }
    .page-subtitle { color:#8fa8c2;font-size:13px;margin-top:3px; }
    .top-pill { border:1px solid rgba(55,214,160,.25);background:rgba(55,214,160,.08);
      border-radius:20px;padding:7px 11px;color:#75e7ba;font-size:11px;font-weight:700;white-space:nowrap; }
    .panel {
      background:linear-gradient(145deg,rgba(17,36,58,.94),rgba(11,27,45,.96));
      border:1px solid var(--border);border-radius:16px;padding:17px 18px;
      box-shadow:0 12px 30px rgba(0,0,0,.13);height:100%;
    }
    .panel-label { color:#829bb6;font-size:10px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase; }
    .panel-title { color:#eaf4ff;font:600 16px 'Space Grotesk',sans-serif;margin:4px 0 2px; }
    .panel-sub { color:#7892ae;font-size:11px;margin-bottom:12px; }
    .kpi {
      background:linear-gradient(145deg,rgba(19,43,68,.98),rgba(12,29,48,.98));
      border:1px solid rgba(139,174,207,.16);border-radius:15px;padding:16px 17px;
      min-height:126px;position:relative;overflow:hidden;box-shadow:0 10px 26px rgba(0,0,0,.14);
    }
    .kpi:after { content:"";position:absolute;width:100px;height:100px;right:-35px;top:-42px;
      border-radius:50%;background:rgba(54,217,238,.055); }
    .kpi-top { display:flex;justify-content:space-between;align-items:center; }
    .kpi-label { color:#91a9c3;font-size:10px;letter-spacing:1.2px;text-transform:uppercase;font-weight:800; }
    .kpi-icon { width:29px;height:29px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:14px; }
    .kpi-value { color:#f4f9ff;font:700 30px 'Space Grotesk',sans-serif;margin-top:12px;line-height:1.1; }
    .kpi-foot { color:#7892ae;font-size:10px;margin-top:6px; }
    .kpi-cyan .kpi-icon {background:rgba(54,217,238,.13);color:#58e2f1}
    .kpi-red .kpi-icon {background:rgba(255,100,124,.13);color:#ff8094}
    .kpi-green .kpi-icon {background:rgba(55,214,160,.13);color:#54e2ae}
    .kpi-amber .kpi-icon {background:rgba(246,189,96,.13);color:#ffd18a}
    .section-heading { display:flex;align-items:center;gap:9px;margin:20px 0 10px; }
    .section-dot { width:7px;height:7px;border-radius:50%;background:var(--cyan);box-shadow:0 0 10px rgba(54,217,238,.7); }
    .section-heading span:last-child { color:#e8f3ff;font:600 16px 'Space Grotesk',sans-serif; }
    .muted-note { color:#7892ae;font-size:11px;margin-top:-5px;margin-bottom:12px; }
    .status-chip { display:inline-block;border-radius:20px;padding:4px 9px;font-size:10px;font-weight:800;letter-spacing:.3px; }
    .chip-green {background:rgba(55,214,160,.12);color:#6ce8bb;border:1px solid rgba(55,214,160,.2)}
    .chip-red {background:rgba(255,100,124,.12);color:#ff8b9d;border:1px solid rgba(255,100,124,.2)}
    .chip-amber {background:rgba(246,189,96,.12);color:#ffd18a;border:1px solid rgba(246,189,96,.2)}
    .chip-blue {background:rgba(87,155,255,.12);color:#8bbaff;border:1px solid rgba(87,155,255,.2)}
    .service-row {display:flex;justify-content:space-between;align-items:center;padding:11px 0;border-bottom:1px solid rgba(148,181,214,.09)}
    .service-row:last-child {border-bottom:0}
    .service-name {color:#dcecff;font-size:12px;font-weight:600}
    .service-meta {color:#7892ae;font-size:10px;margin-top:3px}
    .service-ok {color:#68e5b5;font-size:10px;font-weight:800}
    .service-watch {color:#ffd18a;font-size:10px;font-weight:800}
    .callout {background:rgba(54,217,238,.06);border:1px solid rgba(54,217,238,.16);
      border-left:3px solid #36d9ee;border-radius:10px;padding:12px 14px;color:#bcd0e4;font-size:12px;}
    .ai-box {background:linear-gradient(145deg,rgba(35,45,83,.48),rgba(13,31,53,.92));
      border:1px solid rgba(167,139,250,.22);border-radius:15px;padding:17px 18px;}
    .ai-label {color:#c4b5fd;font-size:10px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;}
    div[data-testid="stDataFrame"] {border:1px solid rgba(148,181,214,.16);border-radius:12px;overflow:hidden;}
    .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
      border-radius:9px;border:1px solid rgba(54,217,238,.34);
      background:linear-gradient(110deg,#087f9a,#155e9b);color:white;font-weight:700;
      min-height:41px;transition:all .18s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
      border-color:#71eafa;background:linear-gradient(110deg,#0b9bb7,#1d69b2);color:white;
      box-shadow:0 0 18px rgba(54,217,238,.15);
    }
    button[kind="secondary"] {background:rgba(19,43,68,.8)!important;border-color:var(--border)!important;}
    input,textarea,[data-baseweb="select"]>div {background:#0d1d30!important;color:#e7f2ff!important;border-color:#29415c!important;border-radius:9px!important;}
    [data-testid="stMetric"] {background:#10243a;border:1px solid var(--border);border-radius:12px;padding:12px 14px;}
    [data-testid="stMetricLabel"] {color:#91a9c3!important}
    [data-testid="stMetricValue"] {color:#f1f7ff!important}
    [data-testid="stExpander"] {border:1px solid var(--border);border-radius:11px;background:rgba(13,29,48,.7);}
    [data-testid="stFileUploader"] {background:rgba(13,29,48,.65);border:1px dashed #36536f;border-radius:12px;padding:8px;}
    hr {border-color:rgba(148,181,214,.13)!important}
    .footer {text-align:center;color:#526d88;font-size:10px;letter-spacing:.5px;padding:22px 0 5px;}
    @media(max-width:800px){.page-title{font-size:24px}.kpi-value{font-size:25px}.block-container{padding-left:1rem;padding-right:1rem}}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------ SHARED HELPERS ------------------------------
def page_header(title, subtitle, tag="OPERATIONS CONTROL CENTER"):
    st.markdown(
        f"""
        <div class="topline">
          <div>
            <div class="eyebrow">{tag}</div>
            <div class="page-title">{title}</div>
            <div class="page-subtitle">{subtitle}</div>
          </div>
          <div class="top-pill">● SYSTEM ONLINE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def section_title(title, subtitle=None):
    st.markdown(
        f'<div class="section-heading"><span class="section-dot"></span><span>{title}</span></div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(f'<div class="muted-note">{subtitle}</div>', unsafe_allow_html=True)

def kpi_card(label, value, note, icon, tone="cyan"):
    st.markdown(
        f"""
        <div class="kpi kpi-{tone}">
          <div class="kpi-top"><span class="kpi-label">{label}</span><span class="kpi-icon">{icon}</span></div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-foot">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def panel_open(label, title, subtitle=""):
    st.markdown(
        f'<div class="panel"><div class="panel-label">{label}</div><div class="panel-title">{title}</div><div class="panel-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )

def panel_close():
    st.markdown("</div>", unsafe_allow_html=True)

def style_chart(fig, height=320, show_legend=True):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#a9bfd5", family="DM Sans", size=11),
        title_font=dict(color="#eaf4ff", size=15),
        margin=dict(l=8, r=8, t=24, b=8),
        height=height,
        showlegend=show_legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-.18),
    )
    fig.update_xaxes(gridcolor="rgba(148,181,214,.08)", zerolinecolor="rgba(148,181,214,.08)", linecolor="rgba(148,181,214,.12)")
    fig.update_yaxes(gridcolor="rgba(148,181,214,.08)", zerolinecolor="rgba(148,181,214,.08)", linecolor="rgba(148,181,214,.12)")
    return fig

def analyze_logs_rule_based(log_text):
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    error_words = ["ERROR", "EXCEPTION", "FAILED", "FAILURE", "TIMEOUT", "CRITICAL", "FATAL"]
    warning_words = ["WARNING", "WARN"]
    errors = [line for line in lines if any(word in line.upper() for word in error_words)]
    warnings = [line for line in lines if any(word in line.upper() for word in warning_words)]
    critical = [line for line in errors if any(word in line.upper() for word in ["CRITICAL", "FATAL", "PAYMENT FAILURE", "DATABASE DOWN"])]
    normalized = {}
    for line in errors:
        message = re.sub(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+", "", line).strip()
        normalized[message] = normalized.get(message, 0) + 1
    repeated = [{"Error Message": msg, "Occurrences": count} for msg, count in normalized.items() if count > 1]
    repeated.sort(key=lambda x: x["Occurrences"], reverse=True)
    severity_rows = []
    for line in lines:
        upper = line.upper()
        if any(word in upper for word in ["CRITICAL", "FATAL", "DATABASE DOWN", "PAYMENT FAILURE"]):
            level = "Critical"
        elif any(word in upper for word in ["ERROR", "EXCEPTION", "FAILED", "FAILURE", "TIMEOUT"]):
            level = "High"
        elif any(word in upper for word in warning_words):
            level = "Medium"
        else:
            level = "Low"
        severity_rows.append({"Log Message": line, "Severity": level})
    return lines, errors, warnings, critical, repeated, pd.DataFrame(severity_rows)

def get_rca_rules():
    return [
        {"service":"Database Service","keywords":["DATABASE","SQL","CONNECTION"],"cause":"Possible database unavailability, network connectivity issue, or connection limit.","checks":["Verify database availability.","Check connection configuration and pool usage.","Review database and network logs."]},
        {"service":"API Service","keywords":["API","HTTP","REQUEST","RESPONSE","TIMEOUT"],"cause":"Possible API latency, downstream service delay, or request timeout.","checks":["Check response times and HTTP status codes.","Verify downstream service health.","Inspect API gateway logs and timeout settings."]},
        {"service":"Payment Service","keywords":["PAYMENT","TRANSACTION","REFUND"],"cause":"Possible payment processing failure or dependency issue. Transaction status needs verification.","checks":["Verify transaction status with the payment system.","Review gateway response codes.","Check duplicate-payment risk before retrying."]},
        {"service":"Authentication Service","keywords":["AUTH","LOGIN","TOKEN"],"cause":"Possible authentication, token expiry, or credential validation issue.","checks":["Verify token expiry and validity.","Check authentication service availability.","Review login and authorization logs."]},
    ]

def generate_ai_analysis(log_text):
    if gemini_client is None:
        return "Gemini AI is not configured. Verify GEMINI_API_KEY in your local .env file and ensure google-genai is installed."
    prompt = f"""
You are SentinelAI, a production technology operations analyst.
Analyze these logs with evidence-based reasoning and use these sections:
1. Incident summary and potential business impact
2. Detected errors, warnings, timestamps and repeated patterns
3. Severity (provisional if impact is not independently verified)
4. Confirmed evidence (quote exact log lines)
5. Unverified assumptions
6. Possible root causes (evidence, missing evidence, verification)
7. L1/L2/L3 troubleshooting
8. Escalation recommendation
9. Prevention recommendations
10. Final assessment and next action

Never invent facts, timestamps, metrics or services. Separate evidence from hypotheses.
An error alone does not prove infrastructure failure. Do not claim financial impact without evidence.
A completed health check does not prove recovery. Confirm recovery only with successful health checks
or transactions. Explain when evidence is insufficient.

APPLICATION LOGS:
{log_text}
"""
    try:
        response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return response.text or "Gemini returned an empty response."
    except Exception as exc:
        return f"Gemini AI analysis error: {exc}"

def generate_incident_pdf(report_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("SentinelTitle", parent=styles["Title"], textColor=colors.HexColor("#12304a"), fontSize=22, leading=26)
    cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=7, leading=9, wordWrap="CJK")
    header = ParagraphStyle("Header", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    total = len(report_df)
    critical = int((report_df["severity"] == "Critical").sum())
    high = int((report_df["severity"] == "High").sum())
    resolved = int(report_df["status"].isin(["Resolved", "Closed"]).sum())
    elements = [
        Paragraph("SENTINELAI", title_style),
        Paragraph("Incident Intelligence | Operations Analytics Report", styles["Heading2"]),
        Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}", styles["Normal"]),
        Spacer(1, 15),
    ]
    summary = [["Metric","Count"],["Total incidents",str(total)],["Critical incidents",str(critical)],["High incidents",str(high)],["Resolved incidents",str(resolved)],["Pending incidents",str(total-resolved)]]
    summary_table = Table(summary, colWidths=[210,90])
    summary_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123b5a")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#bdcbd8")),("PADDING",(0,0),(-1,-1),7),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]))
    elements += [Paragraph("Executive Summary",styles["Heading2"]),summary_table,Spacer(1,15),Paragraph("Incident Register",styles["Heading2"])]
    columns = ["incident_id","title","severity","assigned_team","status","created_at"]
    labels = ["Incident ID","Title","Severity","Assigned Team","Status","Created At"]
    data = [[Paragraph(x,header) for x in labels]]
    for _, row in report_df[columns].iterrows():
        data.append([Paragraph(str(row[c]),cell) for c in columns])
    table = Table(data,repeatRows=1,colWidths=[105,145,60,125,75,105])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123b5a")),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#bdcbd8")),("PADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def severity_color(level):
    return {"Critical":"#ff647c","High":"#f6bd60","Medium":"#579bff","Low":"#37d6a0"}.get(level,"#91a8c2")

# ------------------------------ SIDEBAR ------------------------------
PAGES = [
    "Operations Dashboard",
    "Log Analyzer",
    "Incident Management",
    "Root Cause Analysis",
    "Reports & Analytics",
    "System Information",
]
PAGE_ICONS = {
    "Operations Dashboard":"◈",
    "Log Analyzer":"⌁",
    "Incident Management":"▣",
    "Root Cause Analysis":"⌘",
    "Reports & Analytics":"▥",
    "System Information":"⚙",
}
with st.sidebar:
    st.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-mark">🛡️</div>
          <div><div class="brand-name">SentinelAI</div><div class="brand-tag">INCIDENT INTELLIGENCE</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-small">WORKSPACE NAVIGATION</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        PAGES,
        format_func=lambda item: f"{PAGE_ICONS[item]}   {item}",
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(
        '<div class="side-status"><span class="pulse"></span><span style="font-size:11px;font-weight:700;color:#79e9bd">All local services operational</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("VERSION 2.0  •  ENTERPRISE UI")
    st.caption("AI-assisted · Evidence-led operations")
    st.markdown("---")
    st.markdown('<div class="side-small">AI ENGINE</div>', unsafe_allow_html=True)
    st.markdown(f"**{'Connected' if gemini_client else 'Not configured'}**")
    st.caption(f"Google Gemini · {GEMINI_MODEL}")
    st.markdown("---")
    st.caption("SentinelAI Control Center")

# ------------------------------ OPERATIONS DASHBOARD ------------------------------
if page == "Operations Dashboard":
    page_header("Operations Overview", "A consolidated view of incident posture, service signals and operational workload.")
    df = load_incidents()
    total = len(df)
    critical = int((df["severity"]=="Critical").sum()) if total else 0
    high = int((df["severity"]=="High").sum()) if total else 0
    resolved = int(df["status"].isin(["Resolved","Closed"]).sum()) if total else 0
    pending = int(df["status"].isin(["Open","In Progress","Escalated"]).sum()) if total else 0
    resolution_rate = round((resolved/total)*100) if total else 0

    cols = st.columns(4)
    cards = [
        ("TOTAL INCIDENTS",total,"All records in local incident register","▣","cyan"),
        ("CRITICAL PRIORITY",critical,"Requires immediate investigation","⚠","red"),
        ("ACTIVE WORKLOAD",pending,"Open, in progress or escalated","◷","amber"),
        ("RESOLUTION RATE",f"{resolution_rate}%","Resolved or closed incidents","✓","green"),
    ]
    for col, args in zip(cols,cards):
        with col: kpi_card(*args)

    section_title("Operational intelligence","Incident distribution and volume based on the local SQLite incident register.")
    left,right = st.columns([1.12,1])
    with left:
        panel_open("INCIDENT TELEMETRY","Severity distribution","Breakdown by operational priority")
        if total:
            severity_data = df["severity"].value_counts().reindex(SEVERITIES,fill_value=0).reset_index()
            severity_data.columns=["Severity","Incidents"]
            fig=px.pie(severity_data,names="Severity",values="Incidents",hole=.70,
                       color="Severity",color_discrete_map={"Critical":"#ff647c","High":"#f6bd60","Medium":"#579bff","Low":"#37d6a0"})
            fig.update_traces(textposition="outside",textinfo="percent+label",hole=.70,marker=dict(line=dict(color="#0b1b2e",width=3)))
            fig.add_annotation(text=f"<b>{total}</b><br><span style='font-size:10px;color:#8fa8c2'>TOTAL</span>",showarrow=False,font=dict(size=23,color="#f4f9ff"))
            st.plotly_chart(style_chart(fig,300),use_container_width=True,config={"displayModeBar":False})
        else:
            st.markdown('<div class="callout">No incident records yet. Create an incident to populate operational telemetry.</div>',unsafe_allow_html=True)
        panel_close()
    with right:
        panel_open("WORKLOAD TREND","Incident activity · 7 days","Daily incident creation volume")
        dates=pd.date_range(end=pd.Timestamp.today().normalize(),periods=7)
        if total:
            created=pd.to_datetime(df["created_at"],errors="coerce")
            counts=created.dropna().dt.normalize().value_counts()
            values=[int(counts.get(day,0)) for day in dates]
        else: values=[0]*7
        daily=pd.DataFrame({"Date":dates.strftime("%a"),"Incidents":values})
        fig=px.bar(daily,x="Date",y="Incidents",text="Incidents")
        fig.update_traces(marker_color="#27bfd6",marker_line_color="#73e8f4",marker_line_width=1,textposition="outside")
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(style_chart(fig,300,False),use_container_width=True,config={"displayModeBar":False})
        panel_close()

    section_title("Service health snapshot","Illustrative service indicators derived from detected incident records, not live infrastructure probes.")
    services = [
        ("Database Service","Connection and query signals","Operational" if not (total and df["title"].str.contains("database",case=False,na=False).any() and pending) else "Attention"),
        ("API Gateway","Latency and request signals","Operational"),
        ("Payment Service","Transaction processing signals","Operational" if not (total and df["title"].str.contains("payment",case=False,na=False).any() and pending) else "Attention"),
        ("Authentication","Identity and token signals","Operational"),
    ]
    s_cols=st.columns(4)
    for col,(name,desc,status) in zip(s_cols,services):
        with col:
            panel_open("SERVICE MONITOR",name,desc)
            if status=="Operational":
                st.markdown('<span class="status-chip chip-green">● MONITORING</span>',unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-chip chip-amber">● REVIEW SIGNALS</span>',unsafe_allow_html=True)
            panel_close()

    section_title("Recent incident activity","Most recently created incidents.")
    if total:
        recent=df.head(8)[["incident_id","title","severity","assigned_team","status","created_at"]].copy()
        st.dataframe(recent,use_container_width=True,hide_index=True)
    else:
        st.info("No incidents are registered yet. Use Incident Management to create your first ticket.")
    st.markdown('<div class="footer">SENTINELAI • OPERATIONAL INTELLIGENCE • LOCAL DATABASE TELEMETRY</div>',unsafe_allow_html=True)

# ------------------------------ LOG ANALYZER ------------------------------
elif page == "Log Analyzer":
    page_header("Log Intelligence", "Inspect application telemetry, detect patterns and generate evidence-led AI assessments.", "OBSERVABILITY / LOG ANALYSIS")
    st.markdown('<div class="callout">Upload a log file or paste raw application events. Rule-based detection runs locally; Gemini AI provides a separate analytical assessment.</div>',unsafe_allow_html=True)
    left,right=st.columns([1.08,.92])
    with left:
        panel_open("INPUT SOURCE","Log ingestion","Supported formats: TXT · LOG · CSV")
        uploaded=st.file_uploader("Choose a log file",type=["txt","log","csv"],label_visibility="collapsed")
        pasted=st.text_area("Paste application logs",height=230,placeholder="2026-11-20 10:30:00 ERROR Database connection failed...")
        log_text=pasted
        if uploaded is not None:
            log_text=uploaded.getvalue().decode("utf-8",errors="replace")
            st.caption(f"Loaded file: {uploaded.name} · {len(log_text.splitlines())} lines")
        st.caption("Input is processed for this session. Uploaded log files are not automatically stored in the database.")
        panel_close()
    with right:
        panel_open("ANALYSIS ENGINE","Choose an analysis mode","Run deterministic rules, Gemini AI, or both.")
        st.markdown('<div class="ai-box"><div class="ai-label">✦ GEMINI AI ENGINE</div><div style="color:#e9e6ff;font-size:16px;font-weight:700;margin:8px 0 4px">Context-aware incident assessment</div><div style="color:#a99fd0;font-size:11px">Summaries · hypotheses · troubleshooting · escalation · prevention</div></div>',unsafe_allow_html=True)
        st.write("")
        st.markdown(f'<span class="status-chip {"chip-green" if gemini_client else "chip-amber"}">● {"GEMINI CONNECTED" if gemini_client else "GEMINI NOT CONFIGURED"}</span>',unsafe_allow_html=True)
        run_rules=st.button("⌁  Run rule-based analysis",type="primary",use_container_width=True)
        run_ai=st.button("✦  Generate Gemini assessment",use_container_width=True)
        panel_close()

    if run_rules:
        if not log_text.strip():
            st.warning("Please upload or paste log data first.")
        else:
            lines,errors,warnings,critical_matches,repeated,severity_df=analyze_logs_rule_based(log_text)
            st.session_state["sentinel_log_result"]={
                "lines":lines,"errors":errors,"warnings":warnings,"critical":critical_matches,
                "repeated":repeated,"severity_df":severity_df,"source":uploaded.name if uploaded else "Pasted logs"
            }
    if run_ai:
        if not log_text.strip():
            st.warning("Please upload or paste log data first.")
        else:
            with st.spinner("Gemini is reviewing the supplied evidence..."):
                st.session_state["sentinel_ai_result"]=generate_ai_analysis(log_text)

    result=st.session_state.get("sentinel_log_result")
    if result:
        section_title("Analysis snapshot",f"Source: {result['source']} · Rule-based classification")
        lines,errors,warnings,critical_matches=result["lines"],result["errors"],result["warnings"],result["critical"]
        m=st.columns(4)
        for col,args in zip(m,[
            ("LOG LINES",len(lines),"cyan","≡"),("ERROR EVENTS",len(errors),"red","!"),
            ("WARNING EVENTS",len(warnings),"amber","△"),("CRITICAL MATCHES",len(critical_matches),"red","⚠")
        ]):
            with col:kpi_card(args[0],args[1],"Detected in supplied logs",args[3],args[2])
        a,b=st.columns(2)
        with a:
            panel_open("PATTERN DETECTION","Repeated error signatures","Identical messages after timestamp normalization")
            if result["repeated"]:st.dataframe(pd.DataFrame(result["repeated"]),use_container_width=True,hide_index=True)
            else:st.markdown('<span class="status-chip chip-green">NO REPEATED PATTERNS DETECTED</span>',unsafe_allow_html=True)
            panel_close()
        with b:
            panel_open("SEVERITY CLASSIFICATION","Event priority distribution","Automated preliminary classification")
            sev_counts=result["severity_df"]["Severity"].value_counts().reindex(SEVERITIES,fill_value=0).reset_index()
            sev_counts.columns=["Severity","Events"]
            fig=px.bar(sev_counts,x="Severity",y="Events",color="Severity",text="Events",
                       color_discrete_map={"Critical":"#ff647c","High":"#f6bd60","Medium":"#579bff","Low":"#37d6a0"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(style_chart(fig,260,False),use_container_width=True,config={"displayModeBar":False})
            panel_close()
        section_title("Detected error events","Exact matching log lines.")
        if errors:
            for line in errors:
                st.markdown(f'<div style="background:rgba(255,100,124,.07);border:1px solid rgba(255,100,124,.16);border-left:3px solid #ff647c;border-radius:8px;padding:9px 12px;margin:5px 0;color:#ffc1cb;font:11px monospace">{line}</div>',unsafe_allow_html=True)
        else:st.success("No matching error keywords detected.")
        section_title("Evidence-based service indicators","These are candidate service associations, not confirmed root causes.")
        findings=[]
        for rule in get_rca_rules():
            evidence=[line for line in lines if any(word in line.upper() for word in rule["keywords"])]
            if evidence:findings.append((rule,evidence))
        if findings:
            for rule,evidence in findings:
                with st.expander(f"{rule['service']}  ·  {len(evidence)} matching entries"):
                    st.markdown("**Observed evidence**")
                    for item in evidence:st.code(item)
                    st.markdown("**Possible cause (hypothesis)**")
                    st.write(rule["cause"])
                    st.markdown("**Recommended verification**")
                    for check in rule["checks"]:st.write(f"• {check}")
                    st.warning("Validate against service metrics, health checks and additional logs.")
        else:st.info("No recognized service-related patterns were found.")
        section_title("Event register","Severity assigned to each non-empty log line.")
        st.dataframe(result["severity_df"],use_container_width=True,hide_index=True)
        sev_counts2=result["severity_df"]["Severity"].value_counts().reindex(SEVERITIES,fill_value=0)
        escalation=[]
        for line in lines:
            upper=line.upper()
            if any(w in upper for w in ["CRITICAL","FATAL","DATABASE DOWN"]):team,priority,reason="L3 Engineering","Immediate","Critical failure indicator"
            elif any(w in upper for w in ["DATABASE","SQL","CONNECTION","PAYMENT","TRANSACTION","API","TIMEOUT"]):team,priority,reason="L2 Application Support","High","Application or dependency investigation"
            elif any(w in upper for w in ["WARNING","WARN"]):team,priority,reason="L1 Operations","Monitor","Initial operational verification"
            else:team,priority,reason="L1 Operations","Normal","Routine log entry"
            escalation.append({"Log Message":line,"Assigned Team":team,"Priority":priority,"Reason":reason})
        e_df=pd.DataFrame(escalation)
        x1,x2=st.columns(2)
        with x1:st.download_button("↓  Download error records CSV",pd.DataFrame({"Event ID":range(1,len(errors)+1),"Log Message":errors}).to_csv(index=False).encode("utf-8"),"SentinelAI_Error_Report.csv","text/csv",use_container_width=True)
        with x2:st.download_button("↓  Download escalation CSV",e_df.to_csv(index=False).encode("utf-8"),"SentinelAI_Escalation_Report.csv","text/csv",use_container_width=True)
        st.markdown('<div class="callout">Rule-based analysis identifies preliminary log patterns. Severity is an automated signal, not a substitute for impact assessment. RCA findings remain hypotheses until independently verified.</div>',unsafe_allow_html=True)

    ai_result=st.session_state.get("sentinel_ai_result")
    if ai_result:
        section_title("Gemini AI incident assessment","AI-generated decision support based on the supplied log text.")
        st.markdown('<div class="ai-box"><div class="ai-label">✦ SENTINELAI INTELLIGENCE ENGINE</div></div>',unsafe_allow_html=True)
        st.markdown(ai_result)

# ------------------------------ INCIDENT MANAGEMENT ------------------------------
elif page == "Incident Management":
    page_header("Incident Command", "Create, assign, prioritize and track operational incidents through their lifecycle.", "SERVICE MANAGEMENT / TICKETS")
    df=load_incidents()
    total=len(df)
    open_count=int((df["status"]=="Open").sum()) if total else 0
    progress_count=int((df["status"]=="In Progress").sum()) if total else 0
    escalated=int((df["status"]=="Escalated").sum()) if total else 0
    resolved=int(df["status"].isin(["Resolved","Closed"]).sum()) if total else 0
    metrics=st.columns(4)
    for col,args in zip(metrics,[("TOTAL TICKETS",total,"All registered tickets","▣","cyan"),("OPEN",open_count,"Awaiting action","◷","amber"),("IN PROGRESS",progress_count,"Currently being investigated","↗","cyan"),("RESOLVED",resolved,"Resolved or closed","✓","green")]):
        with col:kpi_card(*args)
    section_title("Incident intake","Register a new operational event.")
    with st.form("incident_creation_form",clear_on_submit=True):
        f1,f2=st.columns([1.2,.8])
        with f1:
            title=st.text_input("Incident title",placeholder="e.g. Payment API transaction failures")
            description=st.text_area("Incident description",placeholder="Describe the observed symptoms, affected service and available evidence...",height=110)
        with f2:
            severity=st.selectbox("Severity",SEVERITIES,index=1)
            team=st.selectbox("Assigned team",TEAMS)
            st.caption("New incidents are created with status: Open.")
        submitted=st.form_submit_button("＋  Create incident",type="primary",use_container_width=True)
        if submitted:
            if not title.strip():st.error("Incident title is required.")
            else:
                now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                incident_id="INC-"+datetime.now().strftime("%Y%m%d%H%M%S%f")
                with get_database_connection() as connection:
                    connection.execute("""INSERT INTO incidents
                    (incident_id,title,description,severity,assigned_team,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?)""",(incident_id,title.strip(),description.strip(),severity,team,"Open",now,now))
                st.success(f"Incident created successfully: {incident_id}")
                st.rerun()
    section_title("Incident register","Filter and inspect the current ticket queue.")
    if df.empty:
        st.info("No incidents are available. Create the first incident using the intake form.")
    else:
        f1,f2,f3=st.columns([1,1,1.4])
        with f1:status_filter=st.selectbox("Filter by status",["All"]+STATUSES)
        with f2:severity_filter=st.selectbox("Filter by severity",["All"]+SEVERITIES)
        with f3:search=st.text_input("Search incidents",placeholder="Search ID or title...")
        view=df.copy()
        if status_filter!="All":view=view[view["status"]==status_filter]
        if severity_filter!="All":view=view[view["severity"]==severity_filter]
        if search.strip():
            mask=view["incident_id"].str.contains(search,case=False,na=False)|view["title"].str.contains(search,case=False,na=False)
            view=view[mask]
        st.caption(f"Showing {len(view)} of {total} incidents")
        st.dataframe(view[["incident_id","title","severity","assigned_team","status","created_at","updated_at"]],use_container_width=True,hide_index=True)
        section_title("Lifecycle control","Update the workflow status of an existing incident.")
        u1,u2,u3=st.columns([1.2,1,1])
        with u1:selected=st.selectbox("Incident ID",df["incident_id"].tolist())
        with u2:new_status=st.selectbox("New status",STATUSES)
        with u3:
            st.write("")
            st.write("")
            update=st.button("Update status",type="primary",use_container_width=True)
        if update:
            with get_database_connection() as connection:
                connection.execute("UPDATE incidents SET status=?,updated_at=? WHERE incident_id=?",(new_status,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),selected))
            st.success(f"{selected} updated to {new_status}.")
            st.rerun()
        with st.expander("View selected incident details"):
            selected_row=df[df["incident_id"]==selected].iloc[0]
            st.markdown(f"**{selected_row['title']}**")
            st.write(selected_row["description"] or "No description provided.")
            st.caption(f"Assigned: {selected_row['assigned_team']} · Created: {selected_row['created_at']} · Updated: {selected_row['updated_at']}")

# ------------------------------ ROOT CAUSE ANALYSIS ------------------------------
elif page == "Root Cause Analysis":
    page_header("Root Cause Intelligence", "Correlate service-related log evidence and structure the next investigation steps.", "PROBLEM MANAGEMENT / RCA")
    st.markdown('<div class="callout">SentinelAI identifies indicators and candidate explanations. It does not claim a root cause is confirmed without independent validation.</div>',unsafe_allow_html=True)
    sample_logs="""2026-11-20 10:02:15 ERROR Database connection failed
2026-11-20 10:02:18 ERROR Database connection failed
2026-11-20 10:03:20 WARNING API response time is high
2026-11-20 10:04:10 ERROR Payment transaction failed TXN1002
2026-11-20 10:05:30 ERROR API request timeout
2026-11-20 10:06:00 CRITICAL DATABASE DOWN
2026-11-20 10:08:20 WARNING Authentication token expires soon"""
    c1,c2=st.columns([1.1,.9])
    with c1:
        panel_open("EVIDENCE INPUT","Application log evidence","Paste or edit the event lines to investigate.")
        input_logs=st.text_area("Log entries",value=sample_logs,height=245,label_visibility="collapsed")
        analyze=st.button("⌕  Analyze root cause indicators",type="primary",use_container_width=True)
        panel_close()
    with c2:
        panel_open("INVESTIGATION MODEL","Service correlation","Rule-based mapping of keywords to service domains.")
        for item in ["Database Service","API Service","Payment Service","Authentication Service"]:
            st.markdown(f'<div class="service-row"><div><div class="service-name">{item}</div><div class="service-meta">Evidence correlation profile</div></div><span class="status-chip chip-blue">READY</span></div>',unsafe_allow_html=True)
        panel_close()
    if analyze:
        lines=[line.strip() for line in input_logs.splitlines() if line.strip()]
        findings=[]
        for rule in get_rca_rules():
            evidence=[line for line in lines if any(word in line.upper() for word in rule["keywords"])]
            if evidence:findings.append((rule,evidence))
        st.session_state["sentinel_rca"]={"lines":lines,"findings":findings}
    rca=st.session_state.get("sentinel_rca")
    if rca:
        section_title("Investigation results","Observed evidence grouped by likely service domain.")
        a,b=st.columns(2)
        a.metric("Log entries",len(rca["lines"]))
        b.metric("Services identified",len(rca["findings"]))
        if rca["findings"]:
            for idx,(rule,evidence) in enumerate(rca["findings"],1):
                with st.expander(f"{idx:02d}  ·  {rule['service']}  ·  {len(evidence)} evidence entries",expanded=True):
                    x,y=st.columns([1.1,.9])
                    with x:
                        st.markdown("**Observed evidence**")
                        for item in evidence:st.code(item)
                    with y:
                        st.markdown("**Possible explanation**")
                        st.write(rule["cause"])
                        st.markdown("**Investigation checklist**")
                        for check in rule["checks"]:st.write(f"□ {check}")
                    st.warning("Hypothesis only — validate using service metrics, health checks, traces and additional logs.")
        else:st.info("No recognized service-related patterns were found.")

# ------------------------------ REPORTS & ANALYTICS ------------------------------
elif page == "Reports & Analytics":
    page_header("Analytics & Reporting", "Explore the incident portfolio and export a shareable operations report.", "INTELLIGENCE / REPORTING")
    df=load_incidents()
    if df.empty:
        st.info("No incident records are available yet. Create incidents to populate the analytics workspace.")
    else:
        total=len(df);critical=int((df["severity"]=="Critical").sum());high=int((df["severity"]=="High").sum())
        resolved=int(df["status"].isin(["Resolved","Closed"]).sum());pending=total-resolved
        rate=round(resolved/total*100)
        cols=st.columns(4)
        for col,args in zip(cols,[("INCIDENTS",total,"Total recorded tickets","▣","cyan"),("CRITICAL + HIGH",critical+high,"Priority 1 and 2 events","⚠","red"),("RESOLVED",resolved,"Resolved or closed","✓","green"),("RESOLUTION RATE",f"{rate}%","Portfolio completion","◈","amber")]):
            with col:kpi_card(*args)
        section_title("Portfolio analytics","Severity, workflow state and incident trend.")
        a,b=st.columns(2)
        with a:
            panel_open("SEVERITY MIX","Incident priority","Portfolio distribution")
            data=df["severity"].value_counts().reindex(SEVERITIES,fill_value=0).reset_index();data.columns=["Severity","Count"]
            fig=px.bar(data,x="Severity",y="Count",color="Severity",text="Count",color_discrete_map={"Critical":"#ff647c","High":"#f6bd60","Medium":"#579bff","Low":"#37d6a0"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(style_chart(fig,290,False),use_container_width=True,config={"displayModeBar":False})
            panel_close()
        with b:
            panel_open("WORKFLOW STATE","Ticket lifecycle","Current status distribution")
            data=df["status"].value_counts().reset_index();data.columns=["Status","Count"]
            fig=px.pie(data,names="Status",values="Count",hole=.64,color_discrete_sequence=["#36d9ee","#579bff","#a78bfa","#37d6a0","#f6bd60"])
            fig.update_traces(textposition="outside",textinfo="label+percent",marker=dict(line=dict(color="#0b1b2e",width=3)))
            st.plotly_chart(style_chart(fig,290),use_container_width=True,config={"displayModeBar":False})
            panel_close()
        section_title("Incident records","Complete records from the local incident database.")
        st.dataframe(df,use_container_width=True,hide_index=True)
        section_title("Export center","Generate downloadable files for review and handover.")
        csv_data=df.to_csv(index=False).encode("utf-8")
        pdf_data=generate_incident_pdf(df)
        summary=f"""SENTINELAI | INCIDENT ANALYTICS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total incidents: {total}
Critical incidents: {critical}
High incidents: {high}
Resolved incidents: {resolved}
Pending incidents: {pending}
Resolution rate: {rate}%

This report is generated from the SentinelAI SQLite incident database.
AI-assisted findings are decision-support outputs and should be validated against authoritative evidence.
"""
        x,y,z=st.columns(3)
        with x:st.download_button("↓  Export CSV",csv_data,"SentinelAI_Incident_Report.csv","text/csv",use_container_width=True)
        with y:st.download_button("↓  Export PDF",pdf_data,"SentinelAI_Incident_Report.pdf","application/pdf",use_container_width=True)
        with z:st.download_button("↓  Export TXT",summary,"SentinelAI_Summary_Report.txt","text/plain",use_container_width=True)

# ------------------------------ SYSTEM INFORMATION ------------------------------
elif page == "System Information":
    page_header("Platform & Configuration", "Runtime details, integration status and operational safeguards.", "PLATFORM / SYSTEM HEALTH")
    section_title("Platform overview","Application runtime and component inventory.")
    details=[
        ("Application","SentinelAI Incident Intelligence Platform","ACTIVE"),
        ("Framework",f"Streamlit {st.__version__}","ACTIVE"),
        ("Database","SQLite · Local persistent storage","CONNECTED"),
        ("AI provider","Google Gemini" if gemini_client else "Google Gemini · Not configured","CONNECTED" if gemini_client else "CHECK CONFIG"),
        ("AI model",GEMINI_MODEL,"READY" if gemini_client else "NOT AVAILABLE"),
        ("Environment","Local development runtime","DEVELOPMENT"),
        ("Data source","sentinelai.db","LOCAL"),
    ]
    for label,value,status in details:
        c1,c2,c3=st.columns([1,2,1])
        c1.markdown(f"**{label}**")
        c2.write(value)
        c3.caption(status)
        st.markdown("<hr style='margin:4px 0 9px'>",unsafe_allow_html=True)
    section_title("Security and operating principles","Safeguards relevant to incident analysis.")
    safeguards=[
        ("Credential handling","Gemini API key is loaded from the local .env file and should never be committed to Git."),
        ("Evidence discipline","Rule-based findings and AI hypotheses are not treated as confirmed root causes."),
        ("Data persistence","Incident records are stored in a local SQLite database."),
        ("Human validation","Critical operational actions should be verified against authoritative system evidence."),
    ]
    for title,desc in safeguards:
        st.markdown(f'<div class="service-row"><div><div class="service-name">{title}</div><div class="service-meta">{desc}</div></div><span class="status-chip chip-green">GUIDANCE</span></div>',unsafe_allow_html=True)

st.markdown('<div class="footer">SENTINELAI 2.0 · AI-POWERED INCIDENT INTELLIGENCE · EVIDENCE BEFORE ASSUMPTION</div>',unsafe_allow_html=True)
