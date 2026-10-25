import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="SDMS | Presentation Workspace",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
    .stApp { background: #f5f7fb; }
    [data-testid="stSidebar"] { background: #172b4d; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .hero {
        background: linear-gradient(120deg, #172b4d, #3568e8);
        color: white; padding: 24px 28px; border-radius: 16px;
        margin-bottom: 20px;
    }
    .hero h1 { color: white; margin: 0; font-size: 28px; }
    .hero p { color: #e3eaff; margin: 7px 0 0; }
    div[data-testid="stMetric"] {
        background: white; padding: 16px; border: 1px solid #e4e9f2;
        border-radius: 12px;
    }
    .section {
        background: white; border: 1px solid #e4e9f2;
        padding: 18px; border-radius: 12px; margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Demo data ----------
def seed_data():
    return {
        "projects": [
            {"Project": "AI Seminar Presentation", "Owner": "Tanisha Akare",
             "Status": "In progress", "Progress (%)": 68, "Due date": date(2026, 11, 5)},
            {"Project": "Software Engineering Case Study", "Owner": "Project Team",
             "Status": "Review", "Progress (%)": 84, "Due date": date(2026, 11, 8)},
            {"Project": "Research Project Proposal", "Owner": "Tanisha Akare",
             "Status": "Planning", "Progress (%)": 25, "Due date": date(2026, 11, 14)},
        ],
        "requirements": [
            {"Requirement": "User registration and login", "Priority": "High",
             "Status": "Approved", "Owner": "Team Leader"},
            {"Requirement": "Presentation templates and slide editor", "Priority": "High",
             "Status": "In progress", "Owner": "Student"},
            {"Requirement": "Role-based access control", "Priority": "High",
             "Status": "In progress", "Owner": "Administrator"},
        ],
        "presentations": [
            {"Title": "AI in Agriculture", "Project": "AI Seminar Presentation",
             "Template": "Academic Blue", "Status": "Draft"},
            {"Title": "Software Development Life Cycle", "Project": "Software Engineering Case Study",
             "Template": "Clean Minimal", "Status": "In review"},
        ],
        "tasks": [
            {"Task": "Prepare project outline", "Assignee": "Tanisha Akare",
             "Priority": "High", "Status": "Done", "Due date": date(2026, 10, 23)},
            {"Task": "Create UML use case diagram", "Assignee": "Team Member 1",
             "Priority": "High", "Status": "In progress", "Due date": date(2026, 10, 28)},
            {"Task": "Review slide formatting", "Assignee": "Faculty / Guide",
             "Priority": "Medium", "Status": "To do", "Due date": date(2026, 10, 30)},
        ],
        "team": [
            {"Name": "Tanisha Akare", "Role": "Student / Project owner", "Email": "tanisha@example.com"},
            {"Name": "Team Member 1", "Role": "Team member", "Email": "member1@example.com"},
            {"Name": "Faculty / Guide", "Role": "Reviewer", "Email": "guide@example.com"},
        ],
        "assessments": [],
    }

if "sdms" not in st.session_state:
    st.session_state.sdms = seed_data()

db = st.session_state.sdms

# ---------- Sidebar ----------
st.sidebar.markdown("## ▣ SDMS")
st.sidebar.caption("Presentation workspace")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "WORKSPACE",
    ["Dashboard", "Projects", "Requirements", "Presentations", "Tasks",
     "Team Collaboration", "Security & Compliance", "Competency Assessment", "Reports"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Student workspace")
st.sidebar.caption("Organize projects, build presentations, collaborate, and track skills.")
st.sidebar.info("Prototype mode: sample data is held in the current Streamlit session.")

# ---------- Helpers ----------
def page_header(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )

def show_table(key):
    rows = db[key]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No records yet. Use the form below to add your first record.")

def csv_download(label, key, filename):
    frame = pd.DataFrame(db[key])
    st.download_button(
        label=label,
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )

# ---------- Pages ----------
if page == "Dashboard":
    page_header("Welcome back, Tanisha 👋", "Here’s what’s happening in your presentation workspace.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active projects", len(db["projects"]))
    c2.metric("Open tasks", sum(t["Status"] != "Done" for t in db["tasks"]))
    c3.metric("Presentations", len(db["presentations"]))
    c4.metric("Requirements", len(db["requirements"]))

    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Recent projects")
        if db["projects"]:
            for p in db["projects"]:
                with st.container(border=True):
                    a, b = st.columns([3, 1])
                    a.markdown(f"**{p['Project']}**")
                    a.caption(f"{p['Owner']} · Due {p['Due date']}")
                    b.write(f"**{p['Progress (%)']}%**")
                    st.progress(int(p["Progress (%)"]) / 100)
                    st.caption(f"Status: {p['Status']}")
        else:
            st.info("No projects created yet.")
    with right:
        st.subheader("Workspace overview")
        st.markdown("""
        - **Content organization:** manage project information and requirements.
        - **Presentation design:** track templates and slide preparation.
        - **Security & compliance:** review access and data-protection practices.
        - **Competency assessment:** record presentation feedback and scores.
        """)
    st.subheader("Quick actions")
    q1, q2, q3, q4 = st.columns(4)
    q1.info("▣  Create a project\n\nUse the Projects page.")
    q2.info("☷  Add requirements\n\nUse the Requirements page.")
    q3.info("▤  Create presentation\n\nUse the Presentations page.")
    q4.info("✓  Create tasks\n\nUse the Tasks page.")

elif page == "Projects":
    page_header("Project Management", "Create projects and monitor their progress.")
    with st.expander("＋ Create project", expanded=False):
        with st.form("project_form", clear_on_submit=True):
            name = st.text_input("Project name", placeholder="e.g., Software Engineering Case Study")
            owner = st.text_input("Project owner", value="Tanisha Akare")
            due = st.date_input("Target completion date", value=date(2026, 11, 15))
            status = st.selectbox("Status", ["Planning", "In progress", "Review", "Completed", "On hold"])
            progress = st.slider("Progress (%)", 0, 100, 0)
            submitted = st.form_submit_button("Save project", type="primary")
            if submitted:
                if name.strip():
                    db["projects"].append({"Project": name.strip(), "Owner": owner.strip(),
                                           "Status": status, "Progress (%)": progress, "Due date": due})
                    st.success("Project added.")
                    st.rerun()
                else:
                    st.error("Please enter a project name.")
    show_table("projects")
    csv_download("Download projects CSV", "projects", "sdms_projects.csv")

elif page == "Requirements":
    page_header("Requirements Management", "Capture functional and non-functional requirements, priorities, and ownership.")
    with st.expander("＋ Add requirement"):
        with st.form("requirement_form", clear_on_submit=True):
            title = st.text_input("Requirement description")
            rtype = st.selectbox("Requirement type", ["Functional", "Non-functional", "Security", "Compliance"])
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"], index=2)
            status = st.selectbox("Status", ["Proposed", "In progress", "Approved", "Blocked"])
            owner = st.text_input("Responsible person")
            submitted = st.form_submit_button("Save requirement", type="primary")
            if submitted:
                if title.strip():
                    db["requirements"].append({"Requirement": title.strip(), "Type": rtype,
                                               "Priority": priority, "Status": status, "Owner": owner.strip()})
                    st.success("Requirement added.")
                    st.rerun()
                else:
                    st.error("Please enter a requirement.")
    show_table("requirements")
    csv_download("Download requirements CSV", "requirements", "sdms_requirements.csv")

elif page == "Presentations":
    page_header("Presentation Studio", "Manage presentation records, template choices, and review status.")
    with st.expander("＋ Create presentation"):
        with st.form("presentation_form", clear_on_submit=True):
            title = st.text_input("Presentation title")
            project_names = [p["Project"] for p in db["projects"]] or ["General"]
            project = st.selectbox("Related project", project_names)
            template = st.selectbox("Template", ["Academic Blue", "Clean Minimal", "Creative", "Corporate"])
            status = st.selectbox("Status", ["Draft", "In review", "Approved"])
            submitted = st.form_submit_button("Save presentation", type="primary")
            if submitted:
                if title.strip():
                    db["presentations"].append({"Title": title.strip(), "Project": project,
                                                "Template": template, "Status": status})
                    st.success("Presentation record added.")
                    st.rerun()
                else:
                    st.error("Please enter a presentation title.")
    show_table("presentations")
    st.caption("This module manages presentation records; it does not yet generate editable PowerPoint files.")
    csv_download("Download presentations CSV", "presentations", "sdms_presentations.csv")

elif page == "Tasks":
    page_header("Task Management", "Assign work, set deadlines, and track task status.")
    with st.expander("＋ Create task"):
        with st.form("task_form", clear_on_submit=True):
            title = st.text_input("Task title")
            assignee = st.text_input("Assignee")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
            status = st.selectbox("Status", ["To do", "In progress", "Done", "Blocked"])
            due = st.date_input("Due date", value=date(2026, 10, 30))
            submitted = st.form_submit_button("Save task", type="primary")
            if submitted:
                if title.strip():
                    db["tasks"].append({"Task": title.strip(), "Assignee": assignee.strip(),
                                        "Priority": priority, "Status": status, "Due date": due})
                    st.success("Task added.")
                    st.rerun()
                else:
                    st.error("Please enter a task title.")
    if db["tasks"]:
        st.subheader("Update task status")
        for i, task in enumerate(db["tasks"]):
            cols = st.columns([3, 1, 1.5])
            cols[0].write(task["Task"])
            cols[1].caption(task["Assignee"])
            options = ["To do", "In progress", "Done", "Blocked"]
            current = options.index(task["Status"]) if task["Status"] in options else 0
            db["tasks"][i]["Status"] = cols[2].selectbox(
                "Status", options, index=current, key=f"task_status_{i}", label_visibility="collapsed"
            )
    show_table("tasks")
    csv_download("Download tasks CSV", "tasks", "sdms_tasks.csv")

elif page == "Team Collaboration":
    page_header("Team Collaboration", "Maintain team contacts and responsibilities.")
    with st.expander("＋ Add team member"):
        with st.form("team_form", clear_on_submit=True):
            name = st.text_input("Full name")
            role = st.selectbox("Role", ["Student", "Team member", "Team leader", "Faculty / Guide", "Administrator"])
            email = st.text_input("Email")
            submitted = st.form_submit_button("Add member", type="primary")
            if submitted:
                if name.strip() and email.strip():
                    db["team"].append({"Name": name.strip(), "Role": role, "Email": email.strip()})
                    st.success("Team member added.")
                    st.rerun()
                else:
                    st.error("Please provide a name and email.")
    show_table("team")
    csv_download("Download team CSV", "team", "sdms_team.csv")

elif page == "Security & Compliance":
    page_header("Security & Compliance", "Review security practices relevant to the project.")
    st.warning("Prototype only: checklist selections do not implement or verify actual security controls.")
    checks = [
        "Passwords are hashed on the server and never stored as plain text.",
        "Role-based access control restricts project and team data.",
        "Data is protected in transit using HTTPS in deployment.",
        "Important actions are recorded in audit logs.",
        "Only authorized users can view or modify project information.",
        "Data collection and retention follow institute policies.",
    ]
    for item in checks:
        st.checkbox(item, key="security_" + str(checks.index(item)))
    st.subheader("Security notes")
    st.write("Production deployment should include server-side authentication, permission checks, secure session handling, input validation, backups, and appropriate data-protection controls.")

elif page == "Competency Assessment":
    page_header("Competency Assessment", "Record feedback and evaluate presentation-related skills.")
    with st.form("assessment_form", clear_on_submit=True):
        student = st.text_input("Student name")
        presentation = st.text_input("Presentation / project")
        content = st.slider("Content organization", 0, 100, 75)
        design = st.slider("Visual design", 0, 100, 75)
        diagrams = st.slider("Diagram quality", 0, 100, 75)
        delivery = st.slider("Presentation delivery", 0, 100, 75)
        collaboration = st.slider("Team collaboration", 0, 100, 75)
        feedback = st.text_area("Feedback")
        submitted = st.form_submit_button("Save assessment", type="primary")
        if submitted:
            if student.strip() and presentation.strip():
                scores = [content, design, diagrams, delivery, collaboration]
                db["assessments"].append({"Student": student.strip(), "Presentation": presentation.strip(),
                    "Content (%)": content, "Design (%)": design, "Diagrams (%)": diagrams,
                    "Delivery (%)": delivery, "Collaboration (%)": collaboration,
                    "Average (%)": round(sum(scores) / len(scores), 1), "Feedback": feedback})
                st.success("Assessment recorded in this session.")
            else:
                st.error("Enter the student and presentation names.")
    if db["assessments"]:
        show_table("assessments")
        csv_download("Download assessments CSV", "assessments", "sdms_assessments.csv")

elif page == "Reports":
    page_header("Reports & Analytics", "Review project status and export workspace records.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projects", len(db["projects"]))
    c2.metric("Tasks completed", sum(t["Status"] == "Done" for t in db["tasks"]))
    c3.metric("Approved requirements", sum(r["Status"] == "Approved" for r in db["requirements"]))
    c4.metric("Team members", len(db["team"]))
    if db["projects"]:
        st.subheader("Project progress")
        chart_df = pd.DataFrame(db["projects"]).set_index("Project")[["Progress (%)"]]
        st.bar_chart(chart_df)
    st.subheader("Export data")
    left, right = st.columns(2)
    with left:
        csv_download("Export projects CSV", "projects", "sdms_projects.csv")
        csv_download("Export requirements CSV", "requirements", "sdms_requirements.csv")
    with right:
        csv_download("Export tasks CSV", "tasks", "sdms_tasks.csv")
        csv_download("Export presentations CSV", "presentations", "sdms_presentations.csv")

st.sidebar.markdown("---")
st.sidebar.caption("SDMS • Front-end academic prototype")
