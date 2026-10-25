"""
SDMS - Software Development & Management System (Streamlit)

Run:
    pip install streamlit pandas
    streamlit run app.py

First run creates sdms.db and an admin account (admin@sdms.edu). Its password is
printed in the terminal once, or set SDMS_ADMIN_PASSWORD before the first run.

Security: salted PBKDF2 password hashes, lockout after 5 failed sign-ins (5 min),
15-minute idle timeout, role-based access (Student / Team leader / Faculty / Admin),
HTML-escaped output, parameterised SQL, CSV formula-injection guard, audit log.
"""
import hashlib, hmac, html, json, os, re, secrets, sqlite3, time, uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdms.db")
IDLE_SECONDS, MAX_FAILS, LOCK_MIN, ITER = 900, 5, 5, 200_000
ROLES = ["Student", "Team leader", "Faculty", "Admin"]
e = lambda v: html.escape(str(v if v is not None else ""))

st.set_page_config(page_title="SDMS", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# ------------------------------------------------------------------ styling
st.markdown("""<style>
.stApp{background:#f3f6fc}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0e2a5e,#0a1d44)}
[data-testid="stSidebar"] *{color:#e6eeff!important}
[data-testid="stSidebar"] [role=radiogroup] label{padding:9px 12px;border-radius:9px;width:100%}
[data-testid="stSidebar"] [role=radiogroup] label:has(input:checked){background:#3b73e8}
[data-testid="stSidebar"] [role=radiogroup] label>div:first-child{display:none}
.block-container{padding-top:1.2rem;max-width:1250px}
.top{background:#fff;border:1px solid #e4e9f2;border-radius:12px;padding:12px 20px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;color:#14213d}
.top h2{margin:0;font-size:20px;color:#14213d}.top small{color:#6b7a99;letter-spacing:.08em}
.av{background:#3b73e8;color:#fff;border-radius:50%;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;margin-left:10px}
.hero{background:#e6efff;border-radius:14px;padding:18px 24px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center}
.hero h1{margin:0;font-size:24px;color:#14213d;padding:0}.hero p{margin:3px 0 0;color:#6b7a99}.hero i{color:#6b7a99}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}
.stat{border-radius:12px;padding:16px 18px;color:#14213d}.stat span{color:#6b7a99}.stat b{display:block;font-size:28px}
.s1{background:#dbe7ff}.s2{background:#ffefd1}.s3{background:#d9f5e3}.s4{background:#ebe3ff}
.card{background:#fff;border:1px solid #e4e9f2;border-radius:12px;padding:16px 18px;margin-bottom:14px;color:#14213d}
.card h3{margin:0 0 10px;font-size:16px;padding:0}
.card table{width:100%;border-collapse:collapse}.card th{background:#f3f6fc;color:#6b7a99;text-align:left;padding:9px;font-size:12.5px}
.card td{padding:10px 9px;border-bottom:1px solid #e4e9f2;font-size:14px}
.b{padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;white-space:nowrap}
.bb{background:#dbe7ff;color:#2d5fd0}.bg{background:#d9f5e3;color:#1b8a4b}.bo{background:#ffefd1;color:#b86e00}.br{background:#fde0e0;color:#c53030}.bn{background:#e4e9f2;color:#6b7a99}
.dl{display:flex;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid #e4e9f2}.dl small{color:#6b7a99}
.dd{width:44px;height:44px;border-radius:50%;background:#dbe7ff;color:#2d5fd0;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:11px;line-height:1.1;flex:none}.dd b{font-size:15px}
.donut{width:150px;height:150px;border-radius:50%;display:grid;place-items:center}.donut div{width:98px;height:98px;border-radius:50%;background:#fff;display:grid;place-items:center;text-align:center;font-size:11px;color:#6b7a99}.donut b{font-size:22px;color:#14213d;display:block}
.act{padding:8px 0;border-bottom:1px solid #e4e9f2}.act small{display:block;color:#6b7a99}
.bar{height:10px;background:#e4e9f2;border-radius:5px;overflow:hidden;margin:4px 0 12px}.bar i{display:block;height:100%;background:#3b73e8}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ database
def run(sql, args=(), fetch=False):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, args)
        rows_ = [dict(r) for r in cur.fetchall()] if fetch else None
        con.commit()
        return rows_
    finally:
        con.close()


def utcnow():
    return datetime.now(timezone.utc)


def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), ITER).hex()
    return f"{salt}${h}"


def check_pw(pw, stored):
    salt, _ = stored.split("$")
    return hmac.compare_digest(hash_pw(pw, salt), stored)


def strong(pw):
    return len(pw) >= 8 and all(re.search(p, pw) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))


def audit(action, user=None):
    u = user or (st.session_state.user["email"] if st.session_state.get("user") else "anonymous")
    run("INSERT INTO audit(ts,user,action) VALUES(?,?,?)", (utcnow().isoformat(timespec="seconds"), u, action))


# entity configuration: (key, label, widget type, options)
STAT = ["Pending", "In Progress", "Completed"]
PRI = ["Low", "Medium", "High", "Critical"]
ENT = {
    "projects": ("My Projects", "project", [("name", "Project name", "text", None), ("owner", "Owner", "text", None), ("status", "Status", "sel", STAT), ("progress", "Progress (%)", "num", None), ("due", "Deadline", "date", None)]),
    "requirements": ("Requirements", "requirement", [("text", "Requirement", "text", None), ("type", "Type", "sel", ["Functional", "Non-functional", "Security", "Compliance"]), ("priority", "Priority", "sel", PRI), ("status", "Status", "sel", ["Proposed", "In Progress", "Approved", "Blocked"]), ("owner", "Responsible", "text", None)]),
    "tasks": ("Tasks", "task", [("title", "Task", "text", None), ("assignee", "Assignee", "text", None), ("priority", "Priority", "sel", PRI[:3]), ("status", "Status", "sel", ["To Do", "In Progress", "Done", "Blocked"]), ("due", "Due date", "date", None)]),
    "presentations": ("Presentations", "presentation", [("title", "Title", "text", None), ("project", "Project", "proj", None), ("template", "Template", "sel", ["Academic Blue", "Clean Minimal", "Creative", "Corporate"]), ("status", "Status", "sel", ["Draft", "In review", "Approved"])]),
    "team": ("Team", "member", [("name", "Full name", "text", None), ("role", "Role", "sel", ["Student", "Team member", "Team leader", "Faculty", "Administrator"]), ("email", "Email", "text", None)]),
    "assess": ("Assessment", "assessment", [("student", "Student", "text", None), ("item", "Presentation / project", "text", None), ("content", "Content", "num", None), ("design", "Design", "num", None), ("diagrams", "Diagrams", "num", None), ("delivery", "Delivery", "num", None), ("feedback", "Feedback", "area", None)]),
}


def init_db():
    run("CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,role TEXT,pw TEXT,fails INT DEFAULT 0,locked_until TEXT)")
    run("CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,entity TEXT,data TEXT,created TEXT)")
    run("CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT,user TEXT,action TEXT)")
    if not run("SELECT 1 FROM users LIMIT 1", fetch=True):
        pw = os.environ.get("SDMS_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        run("INSERT INTO users VALUES(?,?,?,?,?,0,NULL)", (uuid.uuid4().hex, "System Admin", "admin@sdms.edu", "Admin", hash_pw(pw)))
        print(f"\n=== SDMS first run ===\nadmin@sdms.edu  password: {pw}\n======================\n")
        seed = {
            "projects": [("AI Agriculture Dashboard", "Tanisha Akare", "In Progress", 68, "2026-11-15"), ("Sickle Cell Image Classification", "Tanisha Akare", "Completed", 100, "2026-09-30"), ("Self Driving Car Steering", "Tanisha Akare", "Pending", 20, "2026-11-05")],
            "tasks": [("Presentation Preparation", "Tanisha Akare", "High", "In Progress", "2026-10-30"), ("CDC Activity 2", "Tanisha Akare", "Medium", "To Do", "2026-10-28"), ("Create UML use case diagram", "Team Member 1", "High", "To Do", "2026-11-02")],
            "requirements": [("User registration and login", "Security", "High", "Approved", "Team Leader")],
        }
        for ent, items in seed.items():
            keys = [f[0] for f in ENT[ent][2]]
            for r in items:
                run("INSERT INTO records VALUES(?,?,?,?)", (uuid.uuid4().hex[:8], ent, json.dumps(dict(zip(keys, r))), utcnow().isoformat()))
        run("INSERT INTO audit(ts,user,action) VALUES(?,?,?)", (utcnow().isoformat(timespec="seconds"), "system", "Workspace created"))


def rows(ent):
    return [{"id": r["id"], **json.loads(r["data"])} for r in run("SELECT id,data FROM records WHERE entity=? ORDER BY created", (ent,), fetch=True)]


def can(ent, action):
    r = st.session_state.user["role"]
    if r == "Admin":
        return True
    if action == "del" or ent == "team":
        return r == "Team leader"
    if ent == "assess":
        return r != "Student"
    return r != "Faculty"


# ------------------------------------------------------------------ auth
def login(email, pw):
    email = email.strip().lower()
    u = (run("SELECT * FROM users WHERE email=?", (email,), fetch=True) or [None])[0]
    if not u:
        hash_pw(pw)  # keep timing similar for unknown emails
        audit("Failed sign-in", email)
        return "Invalid email or password."
    if u["locked_until"] and datetime.fromisoformat(u["locked_until"]) > utcnow():
        mins = int((datetime.fromisoformat(u["locked_until"]) - utcnow()).total_seconds() // 60) + 1
        return f"Too many attempts. Try again in {mins} min."
    if not check_pw(pw, u["pw"]):
        f = u["fails"] + 1
        if f >= MAX_FAILS:
            run("UPDATE users SET fails=0,locked_until=? WHERE id=?", ((utcnow() + timedelta(minutes=LOCK_MIN)).isoformat(), u["id"]))
            audit(f"Account locked after {MAX_FAILS} failed sign-ins", email)
        else:
            run("UPDATE users SET fails=? WHERE id=?", (f, u["id"]))
            audit("Failed sign-in", email)
        return "Invalid email or password."
    run("UPDATE users SET fails=0,locked_until=NULL WHERE id=?", (u["id"],))
    st.session_state.user = {k: u[k] for k in ("id", "name", "email", "role")}
    st.session_state.last = time.time()
    audit("Signed in")
    return None


def logout(msg=None):
    if st.session_state.get("user"):
        audit("Session expired" if msg else "Signed out")
    for k in ("user", "last"):
        st.session_state.pop(k, None)
    st.session_state.notice = msg


def auth_screen():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div class='hero' style='display:block;text-align:center'><h1>🎓 SDMS</h1><p>Create | Collaborate | Present | Grow</p></div>", unsafe_allow_html=True)
        if st.session_state.get("notice"):
            st.warning(st.session_state.pop("notice"))
        t1, t2 = st.tabs(["Sign in", "Create account"])
        with t1, st.form("login"):
            em, pw = st.text_input("Email"), st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                err = login(em, pw)
                if err:
                    st.error(err)
                else:
                    st.rerun()
        with t2, st.form("signup"):
            nm, em, pw = st.text_input("Full name"), st.text_input("Email address"), st.text_input("Choose password", type="password")
            st.caption("8+ characters with upper, lower, number and symbol.")
            if st.form_submit_button("Create account", type="primary", use_container_width=True):
                if not nm.strip() or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", em.strip()):
                    st.error("Enter your name and a valid email.")
                elif not strong(pw):
                    st.error("Password is too weak.")
                elif run("SELECT 1 FROM users WHERE email=?", (em.strip().lower(),), fetch=True):
                    st.error("That email is already registered.")
                else:
                    run("INSERT INTO users VALUES(?,?,?,?,?,0,NULL)", (uuid.uuid4().hex, nm.strip()[:60], em.strip().lower(), "Student", hash_pw(pw)))
                    audit("Account created", em.strip().lower())
                    st.success("Account created. Sign in from the first tab.")


# ------------------------------------------------------------------ UI helpers
def badge(v):
    s = str(v).lower()
    c = "bg" if s in ("completed", "done", "approved") else "bb" if s in ("in progress", "in review", "draft") else "bo" if s in ("pending", "to do", "proposed", "medium") else "br" if s in ("blocked", "high", "critical") else "bn"
    return f"<span class='b {c}'>{e(v)}</span>"


def fdate(d):
    try:
        return datetime.fromisoformat(d).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return e(d)


def table(ent, data):
    cols = ENT[ent][2]
    if not data:
        return "<p style='color:#6b7a99'>No records yet.</p>"
    th = "".join(f"<th>{e(c[1])}</th>" for c in cols) + ("<th>Average</th>" if ent == "assess" else "")
    body = ""
    for r in data:
        tds = ""
        for k, _, t, _o in cols:
            v = r.get(k, "")
            tds += f"<td>{badge(v) if k in ('status', 'priority') else fdate(v) if t == 'date' else (str(v) + '%') if k == 'progress' else e(v)}</td>"
        if ent == "assess":
            tds += f"<td><b>{round(sum(int(r[k]) for k in ('content', 'design', 'diagrams', 'delivery')) / 4)}%</b></td>"
        body += f"<tr>{tds}</tr>"
    return f"<table><tr>{th}</tr>{body}</table>"


def goto(p):
    st.session_state.page = p


# ------------------------------------------------------------------ pages
def dashboard():
    u, P, T = st.session_state.user, rows("projects"), rows("tasks")
    cnt = lambda s: sum(p["status"] == s for p in P)
    done, ip, pe = cnt("Completed"), cnt("In Progress"), cnt("Pending")
    n = len(P) or 1
    ov = round(sum(int(p["progress"]) for p in P) / n) if P else 0
    a, b = done / n * 100, (done + ip) / n * 100
    st.markdown(f"<div class='hero'><div><h1>👋 Welcome, {e(u['name'])}!</h1><p>Here’s an overview of your project activities and progress.</p></div><i>“Better presentations build better ideas.”</i></div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='stats'><div class='stat s1'><span>Total Projects</span><b>{len(P)}</b></div>
    <div class='stat s2'><span>Pending Tasks</span><b>{sum(t['status'] != 'Done' for t in T)}</b></div>
    <div class='stat s3'><span>Team Members</span><b>{len(rows('team'))}</b></div><div class='stat s4'><span>Completed</span><b>{done}</b></div></div>""", unsafe_allow_html=True)
    L, R = st.columns([1.9, 1])
    with L:
        st.markdown(f"<div class='card'><h3>My Projects</h3>{table('projects', P[:4])}</div>", unsafe_allow_html=True)
    with R:
        dl = sorted([(t["due"], t["title"], "Task") for t in T if t["status"] != "Done" and t["due"]] + [(p["due"], p["name"], "Project submission") for p in P if p["status"] != "Completed" and p["due"]])[:4]
        items = ""
        for d, nme, kind in dl:
            dt = datetime.fromisoformat(d)
            items += f"<div class='dl'><div class='dd'><b>{dt.day}</b>{dt.strftime('%b')}</div><div>{e(nme)}<br><small>{kind}</small></div></div>"
        st.markdown(f"<div class='card'><h3>📅 Upcoming Deadlines</h3>{items or 'No upcoming deadlines.'}</div>", unsafe_allow_html=True)
    L2, R2 = st.columns([1, 1.2])
    with L2:
        st.markdown(f"""<div class='card'><h3>Project Progress</h3><div style='display:flex;gap:18px;align-items:center;flex-wrap:wrap'>
        <div class='donut' style='background:conic-gradient(#3aa76d 0 {a}%,#3b73e8 {a}% {b}%,#f5b83d {b}% 100%)'><div><span><b>{ov}%</b>Overall Progress</span></div></div>
        <div>🟢 Completed {done}<br>🔵 In Progress {ip}<br>🟡 Pending {pe}</div></div></div>""", unsafe_allow_html=True)
    with R2:
        acts = run("SELECT ts,user,action FROM audit ORDER BY id DESC LIMIT 4", fetch=True)
        st.markdown("<div class='card'><h3>🕒 Recent Activity</h3>" + "".join(f"<div class='act'>{e(x['action'])}<small>{e(x['user'])} · {e(x['ts'][:16].replace('T', ' '))} UTC</small></div>" for x in acts) + "</div>", unsafe_allow_html=True)
    st.markdown("#### 🔗 Quick links")
    for col, (label, pg) in zip(st.columns(4), [("＋ Create new project", "My Projects"), ("⬆ Add presentation", "Presentations"), ("👥 View team", "Team"), ("📊 Open reports", "Reports")]):
        col.button(label, on_click=goto, args=(pg,), use_container_width=True)


def crud(ent):
    title, noun, cols = ENT[ent]
    data = rows(ent)
    st.markdown(f"<div class='hero'><div><h1>{title}</h1><p>Add, edit and track your {noun} records.</p></div></div>", unsafe_allow_html=True)
    f = st.text_input("🔍 Search", key=f"q_{ent}").lower()
    shown = [r for r in data if f in json.dumps(r).lower()] if f else data
    st.markdown(f"<div class='card'>{table(ent, shown)}</div>", unsafe_allow_html=True)

    def form(prefill, key):
        out = {}
        for k, label, t, opts in cols:
            v, kk = prefill.get(k), f"{key}_{k}"
            if t == "sel":
                out[k] = st.selectbox(label, opts, index=opts.index(v) if v in opts else 0, key=kk)
            elif t == "proj":
                names = [p["name"] for p in rows("projects")] + ["General"]
                out[k] = st.selectbox(label, names, index=names.index(v) if v in names else 0, key=kk)
            elif t == "num":
                out[k] = st.slider(label, 0, 100, int(v or 0), key=kk)
            elif t == "date":
                try:
                    dv = date.fromisoformat(v)
                except (TypeError, ValueError):
                    dv = date.today()
                out[k] = st.date_input(label, dv, key=kk).isoformat()
            elif t == "area":
                out[k] = st.text_area(label, v or "", max_chars=500, key=kk)
            else:
                out[k] = st.text_input(label, v or "", max_chars=120, key=kk)
        return {k: (v.strip() if isinstance(v, str) else v) for k, v in out.items()}

    def invalid(d):
        if not d[cols[0][0]]:
            return f"{cols[0][1]} is required."
        if ent == "team" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", d["email"]):
            return "Enter a valid email address."

    if can(ent, "add"):
        with st.expander(f"＋ Add {noun}"), st.form(f"add_{ent}", clear_on_submit=True):
            d = form({}, f"a_{ent}")
            if st.form_submit_button(f"Save {noun}", type="primary"):
                err = invalid(d)
                if err:
                    st.error(err)
                else:
                    run("INSERT INTO records VALUES(?,?,?,?)", (uuid.uuid4().hex[:8], ent, json.dumps(d), utcnow().isoformat()))
                    audit(f"Added {noun}: {d[cols[0][0]]}")
                    st.rerun()
    else:
        st.caption("Your role has read-only access here.")
    if data and ((can(ent, "edit") and ent != "assess") or can(ent, "del")):
        with st.expander(f"✏️ Edit or delete a {noun}"):
            pick = st.selectbox("Choose record", data, format_func=lambda r: str(r[cols[0][0]]), key=f"pick_{ent}")
            rid = pick["id"]
            if can(ent, "edit") and ent != "assess":
                with st.form(f"edit_{ent}_{rid}"):
                    d = form(pick, f"e_{rid}")
                    if st.form_submit_button("Update", type="primary"):
                        err = invalid(d)
                        if err:
                            st.error(err)
                        else:
                            run("UPDATE records SET data=? WHERE id=? AND entity=?", (json.dumps(d), rid, ent))
                            audit(f"Updated {noun}: {d[cols[0][0]]}")
                            st.rerun()
            if can(ent, "del"):
                if st.checkbox("Confirm delete", key=f"cd_{rid}") and st.button("🗑️ Delete", key=f"del_{rid}"):
                    run("DELETE FROM records WHERE id=? AND entity=?", (rid, ent))
                    audit(f"Deleted {noun}")
                    st.rerun()


def reports():
    st.markdown("<div class='hero'><div><h1>Reports</h1><p>Track progress and export your data.</p></div></div>", unsafe_allow_html=True)
    P, T, R = rows("projects"), rows("tasks"), rows("requirements")
    st.markdown(f"""<div class='stats'><div class='stat s1'><span>Projects</span><b>{len(P)}</b></div><div class='stat s2'><span>Tasks completed</span><b>{sum(t['status'] == 'Done' for t in T)}/{len(T)}</b></div>
    <div class='stat s3'><span>Approved requirements</span><b>{sum(r['status'] == 'Approved' for r in R)}</b></div><div class='stat s4'><span>Assessments</span><b>{len(rows('assess'))}</b></div></div>""", unsafe_allow_html=True)
    if P:
        st.markdown("<div class='card'><h3>Project progress</h3>" + "".join(f"{e(p['name'])} <b style='float:right'>{p['progress']}%</b><div class='bar'><i style='width:{p['progress']}%'></i></div>" for p in P) + "</div>", unsafe_allow_html=True)
    st.subheader("Export data")
    cols = st.columns(3)
    for i, ent in enumerate(ENT):
        df = pd.DataFrame([{k: v for k, v in r.items() if k != "id"} for r in rows(ent)])
        if not df.empty:  # block spreadsheet formula injection
            df = df.map(lambda v: "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v)
        cols[i % 3].download_button(f"⬇ {ENT[ent][0]} CSV", df.to_csv(index=False).encode(), f"sdms_{ent}.csv", "text/csv", use_container_width=True)


def profile():
    u = st.session_state.user
    st.markdown("<div class='hero'><div><h1>Profile</h1><p>Your account and password.</p></div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><b>{e(u['name'])}</b><br>{e(u['email'])}<br>{badge(u['role'])}</div>", unsafe_allow_html=True)
    with st.form("pw"):
        st.subheader("Change password")
        cur, new = st.text_input("Current password", type="password"), st.text_input("New password", type="password")
        if st.form_submit_button("Update password", type="primary"):
            row = run("SELECT pw FROM users WHERE id=?", (u["id"],), fetch=True)[0]
            if not check_pw(cur, row["pw"]):
                st.error("Current password is incorrect.")
            elif not strong(new):
                st.error("New password needs 8+ characters with upper, lower, number and symbol.")
            else:
                run("UPDATE users SET pw=? WHERE id=?", (hash_pw(new), u["id"]))
                audit("Password changed")
                st.success("Password updated.")


def security():
    st.markdown("<div class='hero'><div><h1>Security & Compliance</h1><p>Controls protecting your workspace.</p></div></div>", unsafe_allow_html=True)
    ctl = ["Passwords stored as salted PBKDF2 hashes, never plain text", f"Account lockout for {LOCK_MIN} minutes after {MAX_FAILS} failed sign-ins", "Strong password policy at sign-up and password change",
           f"Automatic sign-out after {IDLE_SECONDS // 60} minutes of inactivity", "Role-based access: Student, Team leader, Faculty, Admin", "Audit log of sign-ins and every change",
           "All displayed data is HTML-escaped; CSV exports block formula injection", "Parameterised SQL for all database access"]
    st.markdown("<div class='card'><h3>Active controls</h3>" + "".join(f"<div class='act'>✅ {c}</div>" for c in ctl) + "<div class='act'>⬜ HTTPS and a production database (set up when you deploy)</div></div>", unsafe_allow_html=True)
    if st.session_state.user["role"] != "Admin":
        st.info("User management and the audit log are visible to administrators only.")
        return
    st.subheader("User accounts")
    for u in run("SELECT * FROM users ORDER BY name", fetch=True):
        c = st.columns([2, 2, 1.5, 1.2])
        c[0].write(u["name"])
        c[1].caption(u["email"])
        me = u["id"] == st.session_state.user["id"]
        new = c[2].selectbox("Role", ROLES, ROLES.index(u["role"]), key=f"r_{u['id']}", disabled=me, label_visibility="collapsed")
        if new != u["role"]:
            run("UPDATE users SET role=? WHERE id=?", (new, u["id"]))
            audit(f"Changed role of {u['email']} to {new}")
            st.rerun()
        if u["locked_until"] and datetime.fromisoformat(u["locked_until"]) > utcnow() and c[3].button("Unlock", key=f"u_{u['id']}"):
            run("UPDATE users SET fails=0,locked_until=NULL WHERE id=?", (u["id"],))
            audit(f"Unlocked {u['email']}")
            st.rerun()
    st.subheader("Audit log")
    st.dataframe(pd.DataFrame(run("SELECT ts AS Time,user AS User,action AS Event FROM audit ORDER BY id DESC LIMIT 100", fetch=True)), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ main
init_db()
if st.session_state.get("user") and time.time() - st.session_state.get("last", 0) > IDLE_SECONDS:
    logout("Session expired after 15 minutes of inactivity.")
if not st.session_state.get("user"):
    auth_screen()
    st.stop()
st.session_state.last = time.time()
user = st.session_state.user

PAGES = ["Dashboard", "My Projects", "Requirements", "Tasks", "Presentations", "Team", "Reports", "Assessment", "Security & Compliance", "Profile"]
ICONS = dict(zip(PAGES, ["🏠", "📁", "📋", "☑️", "🖥️", "👥", "📊", "⭐", "🛡️", "👤"]))
PAGE_ENT = {"My Projects": "projects", "Requirements": "requirements", "Tasks": "tasks", "Presentations": "presentations", "Team": "team", "Assessment": "assess"}
st.session_state.setdefault("page", "Dashboard")
st.sidebar.markdown("## 🎓 SDMS")
page = st.sidebar.radio("Menu", PAGES, key="page", format_func=lambda p: f"{ICONS[p]}  {p}", label_visibility="collapsed")
st.sidebar.button("🚪 Logout", on_click=logout, use_container_width=True)

st.markdown(f"<div class='top'><div><h2>Software Development & Management System</h2><small>Create | Collaborate | Present | Grow</small></div><div><b>{e(user['name'])}</b> · {e(user['role'])}<span class='av'>{e(user['name'][:1].upper())}</span></div></div>", unsafe_allow_html=True)

if page == "Dashboard":
    dashboard()
elif page in PAGE_ENT:
    crud(PAGE_ENT[page])
elif page == "Reports":
    reports()
elif page == "Profile":
    profile()
else:
    security()
