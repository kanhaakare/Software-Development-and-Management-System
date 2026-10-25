import streamlit as st
import datetime
import pandas as pd
import re

# Configure Streamlit page layout
st.set_page_config(page_title="SDMS Student Dashboard", layout="wide", initial_sidebar_state="expanded")

# ------------------ Security Core ------------------
class SecurityScanner:
    @staticmethod
    def sanitize_string(text: str) -> str:
        # Clean standard XSS threats
        clean = re.sub(r'<script.*?>.*?</script>', '[XSS BLOCKED]', text, flags=re.IGNORECASE)
        clean = re.sub(r'javascript:', '[JS BLOCKED]', clean, flags=re.IGNORECASE)
        return clean

    @staticmethod
    def has_sqli(text: str) -> bool:
        sql_patterns = [
            r"'\s*or\s*'",
            r"--",
            r"union\s+select",
            r"select\s+.*\s+from"
        ]
        return any(re.search(pat, text, flags=re.IGNORECASE) for pat in sql_patterns)

# ------------------ Navigation & State ------------------
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = 'Student/Developer'

# Sidebar Control
with st.sidebar:
    st.title("Auth & Access Control")
    role = st.selectbox(
        "Select Active System Role:",
        ["Student/Developer", "Faculty/Guide", "Administrator"],
        key='role_select'
    )
    st.session_state['user_role'] = role

    st.write("-----------")
    st.subheader("Dynamic Project Controls")
    # Dynamic parameters taken from user input
    custom_project_name = st.text_input("Project Name:", value="SDMS Portal")
    custom_kloc = st.number_input("Project Scale (KLOC):", min_value=1.0, max_value=200.0, value=4.0, step=0.5)
    custom_start_date = st.date_input("Timeline Start Date:", datetime.date(2026, 7, 17))

# Sanitization of dynamic input
safe_project_name = SecurityScanner.sanitize_string(custom_project_name)

# ------------------ Header Layer ------------------
st.markdown(f"""
<div style="background-color: #1a237e; padding: 20px; border-radius: 10px; margin-bottom: 25px; color: white;">
    <h1 style='margin: 0;'>{safe_project_name} - SDMS Dashboard</h1>
    <p style='margin: 5px 0 0 0; opacity: 0.85;'>Secure Student Dashboard, Scheduling, and Compliance Portal</p>
</div>
""", unsafe_allow_html=True)

# ------------------ Dynamic Tab Views ------------------
tabs = st.tabs(["Project Overview & Stats", "Tasks & Timeline Layer", "Interactive COCOMO", "Security Testing Layer"])

# TAB 1: OVERVIEW
with tabs[0]:
    st.subheader("Key Project Performance Indicators (KPIs)")
    
    # Recalculate metrics on the fly using custom KLOC input
    a, b, c, d = 2.4, 1.05, 2.5, 0.38
    rec_effort = a * (custom_kloc ** b)
    rec_time = c * (rec_effort ** d)
    rec_staff = rec_effort / rec_time

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Development Scale", value=f"{custom_kloc:.1f} KLOC", delta="Organic Mode")
    with col2:
        st.metric(label="Estimated Effort", value=f"{rec_effort:.2f} PM", delta="COCOMO Standard")
    with col3:
        st.metric(label="Expected Duration", value=f"{rec_time:.2f} Months", delta="Planned Progress")
    with col4:
        st.metric(label="Developer Allocation", value=f"{max(1, int(round(rec_staff)))} Developer(s)", delta="Dynamic Team")

    st.markdown("""
    ### System Scope & Goals
    The SDMS system enables secure creation and validation of project elements and documentation pipelines. This interface utilizes robust client-side input validations to keep development parameters organized and fully audit-compliant.
    """)

# TAB 2: TASKS & SCHEDULING (GANTT CHART)
with tabs[1]:
    st.subheader(f"Active Tasks & Timeline (Starts {custom_start_date.strftime('%d-%m-%Y')})")

    # Generate tasks list based on timeline parameters
    tasks = [
        {"id": "T1", "task": "Requirement Gathering & Analysis", "duration": 5, "dep": "-"},
        {"id": "T2", "task": "Requirement Prioritization", "duration": 3, "dep": "T1"},
        {"id": "T3", "task": "System Design", "duration": 5, "dep": "T2"},
        {"id": "T4", "task": "Database Design", "duration": 4, "dep": "T3"},
        {"id": "T5", "task": "UI/UX Design", "duration": 5, "dep": "T3"},
        {"id": "T6", "task": "Security & Compliance Design", "duration": 4, "dep": "T3"},
        {"id": "T7", "task": "Backend Development", "duration": 10, "dep": "T4"},
        {"id": "T8", "task": "Frontend Development", "duration": 10, "dep": "T5"},
        {"id": "T9", "task": "Team & Collaboration Module", "duration": 5, "dep": "T7, T8"},
        {"id": "T10", "task": "Competency Management Module", "duration": 5, "dep": "T7, T8"},
        {"id": "T11", "task": "Integration", "duration": 4, "dep": "T9, T10"},
        {"id": "T12", "task": "Testing & Debugging", "duration": 7, "dep": "T11"},
        {"id": "T13", "task": "Security Testing", "duration": 4, "dep": "T12"},
        {"id": "T14", "task": "Documentation", "duration": 5, "dep": "T12"},
        {"id": "T15", "task": "Deployment", "duration": 2, "dep": "T13, T14"},
        {"id": "T16", "task": "Maintenance", "duration": 14, "dep": "T15"}
    ]

    rows = []
    task_ends = {}
    for t in tasks:
        if t["id"] == "T1":
            t_start = custom_start_date
        elif t["id"] in ["T4", "T5", "T6"]:
            t_start = task_ends["T3"] + datetime.timedelta(days=1)
        elif t["id"] == "T7":
            t_start = task_ends["T4"] + datetime.timedelta(days=1)
        elif t["id"] == "T8":
            t_start = task_ends["T5"] + datetime.timedelta(days=1)
        elif t["id"] in ["T9", "T10"]:
            t_start = max(task_ends["T7"], task_ends["T8"]) + datetime.timedelta(days=1)
        elif t["dep"] != "-":
            dep_ids = [d.strip() for d in t["dep"].split(",")]
            last_dep_end = max([task_ends[d] for d in dep_ids if d in task_ends])
            t_start = last_dep_end + datetime.timedelta(days=1)
        else:
            t_start = custom_start_date

        t_end = t_start + datetime.timedelta(days=t["duration"] - 1)
        task_ends[t["id"]] = t_end

        rows.append({
            "Task ID": t["id"],
            "Task Description": t["task"],
            "Dependency": t["dep"],
            "Start Date": t_start.strftime("%d-%m-%Y"),
            "Duration (Days)": t["duration"],
            "End Date": t_end.strftime("%d-%m-%Y")
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# TAB 3: INTERACTIVE COCOMO
with tabs[2]:
    st.subheader("Custom COCOMO Estimation Engine")
    st.write("The estimator automatically reflects the dynamic project scale controlled from your sidebar.")
    st.info(f"Current Active Scale Input: {custom_kloc} KLOC")

    c1, c2, c3 = st.columns(3)
    c1.metric("Computed Effort (PM)", f"{rec_effort:.2f}")
    c2.metric("Development Time (Months)", f"{rec_time:.2f}")
    c3.metric("Estimated Staff Level", f"{rec_staff:.2f} Devs")

# TAB 4: SECURITY LAYER
with tabs[3]:
    st.subheader("Live Input Security Validation & Sanitization")
    st.write("Test dynamic inputs against injection and cross-site scripting vulnerabilities.")

    test_string = st.text_input("Input Custom Project Title / Name to check:", value=custom_project_name)

    if test_string:
        sqli_detected = SecurityScanner.has_sqli(test_string)
        sanitized_res = SecurityScanner.sanitize_string(test_string)

        if sqli_detected:
            st.error("Security Alert: Potential SQL Injection vulnerability detected in input pattern!")
        else:
            st.success("Verification: Input is completely free from direct SQL Injection payloads.")

        st.info(f"Sanitized Output Result: {sanitized_res}")
