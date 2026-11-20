# SentinelAI – AI-Powered Incident Analyzer

**Intelligent Incident Management, Log Analysis & Root Cause Analysis Platform**

## 1. Project Overview

SentinelAI is an AI-powered incident analysis platform designed to help Technology Operations teams analyze application logs, identify errors and warning patterns, classify incident severity, and recommend troubleshooting actions.

The platform combines rule-based log analysis with Google Gemini AI to provide structured incident assessments and evidence-based root cause hypotheses.

This prototype uses simulated application logs and a development environment.

## 2. Key Features

- Upload or paste application logs (`.txt`, `.log`, `.csv`).
- Detect errors, warnings, failures and timeouts.
- Identify repeated error patterns.
- Classify incidents as Critical, High, Medium or Low.
- Generate AI-powered incident analysis using Google Gemini.
- Separate confirmed evidence from unverified assumptions.
- Suggest possible root causes and verification methods.
- Recommend L1, L2 and L3 troubleshooting actions.
- Manage incidents with SQLite database persistence.
- View operational dashboards and incident analytics.
- Export incident data as CSV and PDF reports.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Web application interface |
| Pandas | Log and data processing |
| Plotly | Interactive charts |
| SQLite | Incident data storage |
| Google Gemini API | AI-powered incident analysis |
| ReportLab | PDF report generation |

## 4. Application Modules

1. **Operations Dashboard:** Displays incident statistics, severity distribution and recent incidents.
2. **Log Analyzer:** Analyzes uploaded or pasted application logs.
3. **Incident Management:** Creates, stores and updates incident records.
4. **Root Cause Analysis:** Generates possible root causes with supporting evidence and investigation steps.
5. **Reports & Analytics:** Provides visual reports and CSV, TXT and PDF exports.
6. **System Information:** Displays application and development environment details.

## 5. AI Integration

SentinelAI integrates Google Gemini through the `google-genai` Python SDK.

The AI analysis provides:
- Incident summary
- Detected errors and patterns
- Severity classification
- Confirmed evidence
- Unverified assumptions
- Possible root causes
- Immediate troubleshooting steps
- Escalation recommendations
- Prevention recommendations
- Final incident assessment

The system is designed to distinguish verified log evidence from possible explanations. AI-generated root causes are treated as hypotheses until independently verified.

## 6. Installation and Setup

### Prerequisites

- Python 3.12 or later
- pip
- Google Gemini API key

### Step 1: Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd PineLabs_AI_Incident_Analyzer
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

### Step 3: Activate the environment

Windows:

```bash
venv\Scripts\activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Configure the API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

Never publish your actual API key.

### Step 6: Run the application

```bash
streamlit run app.py
```

The application will open in your browser at:

`http://localhost:8501`

## 7. Testing

The prototype was tested using simulated application logs covering different operational scenarios.

| Test Scenario | Expected Behaviour |
|---|---|
| Database connection errors | Detect errors and suggest investigation |
| Repeated error messages | Identify recurring patterns |
| API timeout logs | Detect timeout-related issues |
| Warning-only logs | Avoid unsupported Critical classification |
| Incident creation | Save incident in SQLite |
| Incident status update | Persist updated status |
| Report generation | Export PDF and CSV reports |
| Gemini AI analysis | Generate structured incident assessment |

## 8. Assumptions

- The application uses simulated logs rather than production system data.
- Log messages are treated as evidence only for what they explicitly establish.
- Severity may be provisional when actual business impact is unknown.
- Possible root causes require further investigation and verification.
- The prototype does not directly monitor live production infrastructure.

## 9. Limitations

- AI analysis depends on Gemini API availability and network connectivity.
- AI-generated recommendations require human review.
- The prototype does not connect to real payment gateways or production databases.
- Infrastructure monitoring and automated incident remediation are not implemented.
- Analysis accuracy depends on the quality and completeness of input logs.

## 10. Future Enhancements

- Real-time log monitoring.
- Integration with cloud monitoring platforms.
- Automated incident alerts.
- ServiceNow or Jira integration.
- Advanced log correlation and anomaly detection.
- Role-based access control.
- Kubernetes and container monitoring.

## 11. Project Purpose

SentinelAI demonstrates how AI-assisted log analysis, incident classification, evidence-based troubleshooting and structured reporting can support Technology Operations teams in incident investigation and response.

**Project developed as a Technology Operations case-study prototype for Pine Labs.**