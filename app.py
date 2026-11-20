import os
import re
import sqlite3
from io import BytesIO
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="SentinelAI | Incident Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "SentinelAI"
DB_NAME = "sentinelai.db"
SEVERITIES = ["Critical", "High", "Medium", "Low"]
STATUSES = ["Open", "In Progress", "Escalated", "Resolved", "Closed"]
TEAMS = [
    "L1 Operations",
    "L2 Application Support",
    "L3 Engineering",
    "DevOps & Cloud",
]

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash-lite"

gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        gemini_client = None


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
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
    order = "ASC" if order.upper() == "ASC" else "DESC"
    with get_database_connection() as connection:
        return pd.read_sql_query(
            f"SELECT * FROM incidents ORDER BY id {order}", connection
        )


initialize_database()


# ---------------------------------------------------------
# DESIGN SYSTEM
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --navy: #08111f;
        --panel: #111e31;
        --panel-soft: #16263c;
        --line: #263b55;
        --cyan: #22d3ee;
        --blue: #60a5fa;
        --muted: #9aacc2;
        --white: #edf5ff;
    }

    .stApp {
        background:
            radial-gradient(circle at 85% 0%, rgba(14, 116, 144, .13), transparent 28%),
            linear-gradient(145deg, #08111f 0%, #0b1626 55%, #0a1422 100%);
        color: var(--white);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1728 0%, #101f33 100%);
        border-right: 1px solid #24364d;
    }

    [data-testid="stSidebar"] * {
        color: #dbeafe;
    }

    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    h1, h2, h3 {
        color: #f1f7ff !important;
        letter-spacing: -.025em;
    }

    p, label, [data-testid="stCaptionContainer"] {
        color: #b5c5d8;
    }

    .hero {
        background: linear-gradient(115deg, rgba(17, 38, 62, .98), rgba(12, 31, 49, .92));
        border: 1px solid #29445f;
        border-radius: 18px;
        padding: 22px 26px;
        margin-bottom: 22px;
        box-shadow: 0 12px 34px rgba(0,0,0,.18);
    }

    .hero-kicker {
        color: #67e8f9;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .18em;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .hero-title {
        color: #f8fbff;
        font-size: 30px;
        font-weight: 800;
        margin: 0;
    }

    .hero-subtitle {
        color: #a9bdd3;
        font-size: 14px;
        margin-top: 7px;
    }

    .metric-card {
        background: linear-gradient(145deg, #14263d, #101d30);
        border: 1px solid #2a405b;
        border-radius: 15px;
        padding: 18px 19px;
        min-height: 125px;
        box-shadow: 0 8px 22px rgba(0,0,0,.15);
    }

    .metric-top {
        color: #a9bdd3;
        font-size: 12px;
        font-weight: 650;
        letter-spacing: .04em;
        text-transform: uppercase;
    }

    .metric-number {
        color: #f4f9ff;
        font-size: 32px;
        font-weight: 800;
        line-height: 1.3;
        margin-top: 9px;
    }

    .metric-foot {
        color: #7189a5;
        font-size: 11px;
        margin-top: 3px;
    }

    .section-note {
        color: #8fa6c0;
        font-size: 13px;
        margin-top: -8px;
        margin-bottom: 15px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #263b55;
        border-radius: 12px;
        overflow: hidden;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 9px;
        border: 1px solid #287b9a;
        background: linear-gradient(110deg, #0e7490, #155e9b);
        color: white;
        font-weight: 650;
        min-height: 42px;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: #67e8f9;
        color: white;
        background: linear-gradient(110deg, #0891b2, #1d4ed8);
    }

    input, textarea, [data-baseweb="select"] > div {
        background-color: #101e31 !important;
        color: #e5efff !important;
        border-color: #2a405b !important;
    }

    hr {
        border-color: #263b55;
    }

    [data-testid="stMetric"] {
        background: #122238;
        border: 1px solid #2a405b;
        border-radius: 12px;
        padding: 12px 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #9fb4cc !important;
    }

    [data-testid="stMetricValue"] {
        color: #f4f9ff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SHARED HELPERS
# ---------------------------------------------------------
def metric_card(label, value, note="Live database"):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-top">{label}</div>
            <div class="metric-number">{value}</div>
            <div class="metric-foot">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_chart(fig, height=330):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c6d5e7", family="Arial"),
        title_font=dict(color="#edf5ff", size=16),
        legend_title_font=dict(color="#c6d5e7"),
        margin=dict(l=15, r=15, t=55, b=15),
        height=height,
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(148,163,184,.15)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(148,163,184,.15)")
    return fig


def analyze_logs_rule_based(log_text):
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    error_words = ["ERROR", "EXCEPTION", "FAILED", "FAILURE", "TIMEOUT", "CRITICAL", "FATAL"]
    warning_words = ["WARNING", "WARN"]

    errors = [line for line in lines if any(word in line.upper() for word in error_words)]
    warnings = [line for line in lines if any(word in line.upper() for word in warning_words)]
    critical = [
        line for line in errors
        if any(word in line.upper() for word in ["CRITICAL", "FATAL", "PAYMENT FAILURE", "DATABASE DOWN"])
    ]

    normalized = {}
    for line in errors:
        message = re.sub(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+", "", line).strip()
        normalized[message] = normalized.get(message, 0) + 1

    repeated = [
        {"Error Message": message, "Occurrences": count}
        for message, count in normalized.items() if count > 1
    ]
    repeated.sort(key=lambda item: item["Occurrences"], reverse=True)

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
        {
            "service": "Database Service",
            "keywords": ["DATABASE", "SQL", "CONNECTION"],
            "cause": "Possible database unavailability, network connectivity issue, or connection limit.",
            "checks": ["Verify database availability.", "Check connection configuration and pool usage.", "Review database and network logs."],
        },
        {
            "service": "API Service",
            "keywords": ["API", "HTTP", "REQUEST", "RESPONSE", "TIMEOUT"],
            "cause": "Possible API latency, downstream service delay, or request timeout.",
            "checks": ["Check response times and HTTP status codes.", "Verify downstream service health.", "Inspect API gateway logs and timeout settings."],
        },
        {
            "service": "Payment Service",
            "keywords": ["PAYMENT", "TRANSACTION", "REFUND"],
            "cause": "Possible payment processing failure or dependency issue. Transaction status needs verification.",
            "checks": ["Verify transaction status with the payment system.", "Review gateway response codes.", "Check duplicate-payment risk before retrying."],
        },
        {
            "service": "Authentication Service",
            "keywords": ["AUTH", "LOGIN", "TOKEN"],
            "cause": "Possible authentication, token expiry, or credential validation issue.",
            "checks": ["Verify token expiry and validity.", "Check authentication service availability.", "Review login and authorization logs."],
        },
    ]


def generate_ai_analysis(log_text):
    if gemini_client is None:
        return "Gemini AI is not configured. Check that GEMINI_API_KEY is present in your local .env file and that google-genai is installed."

    prompt = f"""
You are SentinelAI, a production technology operations analyst.
Analyze these logs using evidence-based reasoning. Use these sections:
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

Rules: Never invent facts, timestamps, metrics or services. Clearly separate evidence from hypotheses.
An error alone does not prove infrastructure failure. Do not claim financial impact without evidence.
A completed health check does not prove recovery. Confirm recovery only with successful health checks
or transactions. Explain when evidence is insufficient.

APPLICATION LOGS:
{log_text}
"""
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text or "Gemini returned an empty response."
    except Exception as exc:
        return f"Gemini AI analysis error: {exc}"


def generate_incident_pdf(report_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28,
    )
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=7, leading=9, wordWrap="CJK")
    header = ParagraphStyle("Header", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    elements = [
        Paragraph("<b>SENTINELAI</b>", styles["Title"]),
        Paragraph("Incident Management & Analytics Report", styles["Heading2"]),
        Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}", styles["Normal"]),
        Spacer(1, 16),
    ]

    total = len(report_df)
    critical = int((report_df["severity"] == "Critical").sum())
    high = int((report_df["severity"] == "High").sum())
    resolved = int(report_df["status"].isin(["Resolved", "Closed"]).sum())

    summary = [
        ["Metric", "Count"],
        ["Total incidents", str(total)],
        ["Critical incidents", str(critical)],
        ["High incidents", str(high)],
        ["Resolved incidents", str(resolved)],
        ["Pending incidents", str(total - resolved)],
    ]
    summary_table = Table(summary, colWidths=[210, 90])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .4, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    elements += [Paragraph("Incident Summary", styles["Heading2"]), summary_table, Spacer(1, 16)]
    elements.append(Paragraph("Incident Records", styles["Heading2"]))

    columns = ["incident_id", "title", "severity", "assigned_team", "status", "created_at"]
    labels = ["Incident ID", "Title", "Severity", "Assigned Team", "Status", "Created At"]
    data = [[Paragraph(label, header) for label in labels]]
    for _, row in report_df[columns].iterrows():
        data.append([Paragraph(str(row[column]), cell) for column in columns])

    table = Table(data, repeatRows=1, colWidths=[105, 145, 60, 125, 75, 105])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("GRID", (0, 0), (-1, -1), .4, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------
# SIDEBAR + HEADER
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## 🛡️ SentinelAI")
    st.caption("INCIDENT INTELLIGENCE PLATFORM")
    st.divider()
    page = st.radio(
        "WORKSPACE",
        [
            "Operations Dashboard",
            "Log Analyzer",
            "Incident Management",
            "Root Cause Analysis",
            "Reports & Analytics",
            "System Information",
        ],
    )
    st.divider()
    st.markdown("🟢 **Platform Status: Online**")
    st.caption("Version 1.0.0 · Development Build")
    st.caption("AI-assisted · Evidence-led operations")

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">TECHNOLOGY OPERATIONS / CONTROL CENTER</div>
        <div class="hero-title">🛡️ SentinelAI</div>
        <div class="hero-subtitle">
            AI-powered incident intelligence, monitoring and root cause analysis
            &nbsp; • &nbsp; {datetime.now().strftime("%d %b %Y, %I:%M %p")}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# OPERATIONS DASHBOARD
# ---------------------------------------------------------
if page == "Operations Dashboard":
    st.subheader("Operations Overview")
    st.markdown('<div class="section-note">Real-time operational view from the SentinelAI incident database.</div>', unsafe_allow_html=True)

    df = load_incidents()
    total = len(df)
    critical = int((df["severity"] == "Critical").sum()) if total else 0
    high = int((df["severity"] == "High").sum()) if total else 0
    resolved = int(df["status"].isin(["Resolved", "Closed"]).sum()) if total else 0
    pending = int(df["status"].isin(["Open", "In Progress", "Escalated"]).sum()) if total else 0

    cols = st.columns(4)
    for col, label, value, note in [
        (cols[0], "Total Incidents", total, "All recorded incidents"),
        (cols[1], "Critical Incidents", critical, "Requires urgent attention"),
        (cols[2], "Resolved", resolved, "Resolved or closed"),
        (cols[3], "Active / Pending", pending, "Open, in progress or escalated"),
    ]:
        with col:
            metric_card(label, value, note)

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Severity Distribution")
        if total:
            severity_data = df["severity"].value_counts().reindex(SEVERITIES, fill_value=0).reset_index()
            severity_data.columns = ["Severity", "Incidents"]
            fig = px.pie(severity_data, names="Severity", values="Incidents", hole=.62)
            st.plotly_chart(style_chart(fig, 340), use_container_width=True)
        else:
            st.info("No incident data yet. Create an incident in Incident Management.")

    with right:
        st.subheader("Incident Volume · Last 7 Days")
        if total:
            dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=7)
            created = pd.to_datetime(df["created_at"], errors="coerce")
            counts = created.dropna().dt.normalize().value_counts()
            daily = pd.DataFrame({
                "Day": dates.strftime("%a"),
                "Incidents": [int(counts.get(day, 0)) for day in dates],
            })
            fig = px.bar(daily, x="Day", y="Incidents", text="Incidents")
            st.plotly_chart(style_chart(fig, 340), use_container_width=True)
        else:
            st.info("Incident activity will appear here when records are created.")

    st.divider()
    st.subheader("Recent Incidents")
    if total:
        st.dataframe(
            df[["incident_id", "title", "severity", "assigned_team", "status", "created_at"]].head(8),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No incidents available.")
    st.caption("Dashboard metrics are calculated from the local SQLite database.")


# ---------------------------------------------------------
# LOG ANALYZER
# ---------------------------------------------------------
elif page == "Log Analyzer":
    st.subheader("Advanced Application Log Analyzer")
    st.markdown('<div class="section-note">Upload or paste application logs to identify patterns and support investigation.</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload log file", type=["txt", "log", "csv"])
    pasted = st.text_area(
        "Or paste application logs",
        height=190,
        placeholder="2026-11-20 10:30:00 ERROR Database connection failed...",
    )
    log_text = pasted
    if uploaded is not None:
        log_text = uploaded.getvalue().decode("utf-8", errors="replace")

    if st.button("✨ Analyze with Gemini AI", use_container_width=False):
        if not log_text.strip():
            st.warning("Please upload or paste log data first.")
        else:
            with st.spinner("Gemini AI is analyzing the supplied logs..."):
                result = generate_ai_analysis(log_text)
            st.markdown("### Gemini AI Incident Assessment")
            st.markdown(result)

    if st.button("🔍 Run Rule-Based Log Analysis", type="primary"):
        if not log_text.strip():
            st.warning("Please upload or paste log data first.")
        else:
            lines, errors, warnings, critical_matches, repeated, severity_df = analyze_logs_rule_based(log_text)

            st.divider()
            st.subheader("Analysis Snapshot")
            metric_cols = st.columns(4)
            metric_cols[0].metric("Total Log Lines", len(lines))
            metric_cols[1].metric("Errors", len(errors))
            metric_cols[2].metric("Warnings", len(warnings))
            metric_cols[3].metric("Critical Matches", len(critical_matches))

            st.subheader("Detected Error Events")
            if errors:
                for index, line in enumerate(errors, 1):
                    st.error(f"{index}. {line}")
            else:
                st.success("No matching error keywords detected.")

            st.subheader("Repeated Error Patterns")
            if repeated:
                st.dataframe(pd.DataFrame(repeated), use_container_width=True, hide_index=True)
            else:
                st.success("No repeated error patterns detected.")

            st.subheader("Automated Severity Classification")
            sev_counts = severity_df["Severity"].value_counts().reindex(SEVERITIES, fill_value=0)
            sev_cols = st.columns(4)
            for col, level in zip(sev_cols, SEVERITIES):
                col.metric(f"{level}", int(sev_counts[level]))
            st.dataframe(severity_df, use_container_width=True, hide_index=True)

            st.subheader("Evidence-Based Root Cause Indicators")
            findings = []
            for rule in get_rca_rules():
                evidence = [line for line in lines if any(word in line.upper() for word in rule["keywords"])]
                if evidence:
                    findings.append((rule, evidence))
            if findings:
                for index, (rule, evidence) in enumerate(findings, 1):
                    with st.expander(f"{index}. {rule['service']} · {len(evidence)} matching entries"):
                        st.markdown("**Observed evidence**")
                        for item in evidence:
                            st.code(item)
                        st.markdown("**Possible cause (hypothesis)**")
                        st.write(rule["cause"])
                        st.markdown("**Recommended checks**")
                        for check in rule["checks"]:
                            st.write(f"• {check}")
                        st.warning("Verify this hypothesis using system metrics and additional logs before confirming root cause.")
            else:
                st.info("No recognized service-related patterns were found.")

            st.subheader("Support Escalation Guidance")
            escalation = []
            for line in lines:
                upper = line.upper()
                if any(word in upper for word in ["CRITICAL", "FATAL", "DATABASE DOWN"]):
                    team, priority, reason = "L3 Engineering", "Immediate", "Critical failure indicator"
                elif any(word in upper for word in ["DATABASE", "SQL", "CONNECTION", "PAYMENT", "TRANSACTION", "API", "TIMEOUT"]):
                    team, priority, reason = "L2 Application Support", "High", "Application or dependency investigation"
                elif any(word in upper for word in ["WARNING", "WARN"]):
                    team, priority, reason = "L1 Operations", "Monitor", "Initial operational verification"
                else:
                    team, priority, reason = "L1 Operations", "Normal", "Routine log entry"
                escalation.append({"Log Message": line, "Assigned Team": team, "Priority": priority, "Reason": reason})
            escalation_df = pd.DataFrame(escalation)
            st.dataframe(escalation_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Escalation CSV",
                escalation_df.to_csv(index=False).encode("utf-8"),
                "SentinelAI_Escalation_Report.csv",
                "text/csv",
            )

            st.subheader("Warning Events")
            if warnings:
                for index, line in enumerate(warnings, 1):
                    st.warning(f"{index}. {line}")
            else:
                st.info("No matching warning keywords detected.")

            st.subheader("Error Category Analysis")
            if errors:
                categories = {
                    "Database": ["DATABASE", "SQL", "CONNECTION"],
                    "API": ["API", "HTTP", "REQUEST", "RESPONSE"],
                    "Payment": ["PAYMENT", "TRANSACTION", "REFUND"],
                    "Timeout": ["TIMEOUT", "LATENCY"],
                    "Authentication": ["AUTH", "LOGIN", "TOKEN"],
                }
                pattern_rows = []
                for category, words in categories.items():
                    count = sum(any(word in line.upper() for word in words) for line in errors)
                    pattern_rows.append({"Category": category, "Occurrences": count})
                fig = px.bar(pd.DataFrame(pattern_rows), x="Category", y="Occurrences", text="Occurrences")
                st.plotly_chart(style_chart(fig), use_container_width=True)
                error_df = pd.DataFrame({"Event ID": range(1, len(errors) + 1), "Log Message": errors})
                st.dataframe(error_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Error Records CSV",
                    error_df.to_csv(index=False).encode("utf-8"),
                    "SentinelAI_Error_Report.csv",
                    "text/csv",
                )

            st.info(
                "Rule-based analysis identifies preliminary log patterns. Gemini AI provides additional incident analysis. "
                "RCA findings remain hypotheses until verified using system metrics and logs."
            )


# ---------------------------------------------------------
# INCIDENT MANAGEMENT
# ---------------------------------------------------------
elif page == "Incident Management":
    st.subheader("Incident Management")
    st.markdown('<div class="section-note">Create, assign, track and update operational incidents.</div>', unsafe_allow_html=True)

    with st.form("incident_creation_form", clear_on_submit=True):
        st.markdown("#### Create New Incident")
        title = st.text_input("Incident Title", placeholder="Example: Payment API failure")
        description = st.text_area("Incident Description", placeholder="Describe the observed issue...")
        col_a, col_b = st.columns(2)
        with col_a:
            severity = st.selectbox("Severity", SEVERITIES)
        with col_b:
            team = st.selectbox("Assigned Team", TEAMS)
        submitted = st.form_submit_button("Create Incident", type="primary")

        if submitted:
            if not title.strip():
                st.error("Incident title is required.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                incident_id = "INC-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
                with get_database_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO incidents
                        (incident_id, title, description, severity, assigned_team, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (incident_id, title.strip(), description.strip(), severity, team, "Open", now, now),
                    )
                st.success(f"Incident created successfully: {incident_id}")

    st.divider()
    df = load_incidents()
    st.subheader("Incident Records")
    if df.empty:
        st.info("No incidents available. Create the first incident above.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Tickets", len(df))
        c2.metric("Open Tickets", int((df["status"] == "Open").sum()))
        c3.metric("Resolved / Closed", int(df["status"].isin(["Resolved", "Closed"]).sum()))
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Update Incident Status")
        selected = st.selectbox("Select Incident ID", df["incident_id"].tolist())
        new_status = st.selectbox("New Status", STATUSES)
        if st.button("Update Incident Status"):
            with get_database_connection() as connection:
                connection.execute(
                    "UPDATE incidents SET status = ?, updated_at = ? WHERE incident_id = ?",
                    (new_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected),
                )
            st.success(f"{selected} updated to {new_status}.")
            st.rerun()


# ---------------------------------------------------------
# ROOT CAUSE ANALYSIS
# ---------------------------------------------------------
elif page == "Root Cause Analysis":
    st.subheader("Evidence-Based Root Cause Analysis")
    st.markdown('<div class="section-note">Identify service-related indicators and investigation steps. Findings are hypotheses, not confirmed root causes.</div>', unsafe_allow_html=True)

    sample_logs = """2026-11-20 10:02:15 ERROR Database connection failed
2026-11-20 10:02:18 ERROR Database connection failed
2026-11-20 10:03:20 WARNING API response time is high
2026-11-20 10:04:10 ERROR Payment transaction failed TXN1002
2026-11-20 10:05:30 ERROR API request timeout
2026-11-20 10:06:00 CRITICAL DATABASE DOWN
2026-11-20 10:08:20 WARNING Authentication token expires soon"""

    input_logs = st.text_area("Application Logs", value=sample_logs, height=220)
    if st.button("Analyze Root Cause", type="primary"):
        lines = [line.strip() for line in input_logs.splitlines() if line.strip()]
        if not lines:
            st.warning("Enter log data first.")
        else:
            findings = []
            for rule in get_rca_rules():
                evidence = [line for line in lines if any(word in line.upper() for word in rule["keywords"])]
                if evidence:
                    findings.append((rule, evidence))

            a, b = st.columns(2)
            a.metric("Log Entries", len(lines))
            b.metric("Services Identified", len(findings))
            if findings:
                for index, (rule, evidence) in enumerate(findings, 1):
                    with st.expander(f"{index}. {rule['service']} · {len(evidence)} matching entries", expanded=True):
                        st.markdown("**Observed evidence**")
                        for item in evidence:
                            st.code(item)
                        st.markdown("**Possible cause**")
                        st.write(rule["cause"])
                        st.markdown("**Investigation steps**")
                        for check in rule["checks"]:
                            st.write(f"• {check}")
                        st.warning("Validate this hypothesis with service metrics, health checks and additional logs.")
            else:
                st.info("No recognized service-related patterns were found.")


# ---------------------------------------------------------
# REPORTS & ANALYTICS
# ---------------------------------------------------------
elif page == "Reports & Analytics":
    st.subheader("Reports & Analytics")
    st.markdown('<div class="section-note">Review incident trends and export operational reports.</div>', unsafe_allow_html=True)

    df = load_incidents()
    if df.empty:
        st.info("No incident records available to generate reports.")
    else:
        total = len(df)
        critical = int((df["severity"] == "Critical").sum())
        high = int((df["severity"] == "High").sum())
        resolved = int(df["status"].isin(["Resolved", "Closed"]).sum())

        cols = st.columns(4)
        cols[0].metric("Total Incidents", total)
        cols[1].metric("Critical", critical)
        cols[2].metric("High", high)
        cols[3].metric("Resolved", resolved)

        left, right = st.columns(2)
        with left:
            severity_data = df["severity"].value_counts().reindex(SEVERITIES, fill_value=0).reset_index()
            severity_data.columns = ["Severity", "Incidents"]
            fig = px.bar(severity_data, x="Severity", y="Incidents", text="Incidents")
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with right:
            status_data = df["status"].value_counts().reset_index()
            status_data.columns = ["Status", "Incidents"]
            fig = px.pie(status_data, names="Status", values="Incidents", hole=.55)
            st.plotly_chart(style_chart(fig), use_container_width=True)

        st.divider()
        st.subheader("Complete Incident Records")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Export Reports")
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Incident CSV", csv_data, "SentinelAI_Incident_Report.csv", "text/csv")

        pdf_data = generate_incident_pdf(df)
        st.download_button("Download Professional PDF", pdf_data, "SentinelAI_Incident_Report.pdf", "application/pdf")

        summary = f"""SENTINELAI - INCIDENT ANALYTICS REPORT

Total Incidents: {total}
Critical Incidents: {critical}
High Severity Incidents: {high}
Resolved Incidents: {resolved}
Pending Incidents: {total - resolved}

Generated On: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This report is generated from the SentinelAI SQLite database.
"""
        st.download_button("Download Summary TXT", summary, "SentinelAI_Summary_Report.txt", "text/plain")


# ---------------------------------------------------------
# SYSTEM INFORMATION
# ---------------------------------------------------------
elif page == "System Information":
    st.subheader("System Information")
    st.markdown('<div class="section-note">Application configuration and runtime details.</div>', unsafe_allow_html=True)

    info = [
        ("Platform", "SentinelAI"),
        ("Application", "AI-Powered Incident Intelligence Platform"),
        ("Environment", "Development"),
        ("Framework", f"Streamlit {st.__version__}"),
        ("Database", "SQLite"),
        ("AI Provider", "Google Gemini" if gemini_client else "Not configured"),
        ("AI Model", GEMINI_MODEL),
        ("Data Storage", "Local SQLite database"),
    ]
    for label, value in info:
        left, right = st.columns([1, 2])
        left.markdown(f"**{label}**")
        right.write(value)

    st.divider()
    st.caption("Operational findings are decision-support outputs. Validate critical actions against authoritative system evidence.")
