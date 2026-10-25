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

