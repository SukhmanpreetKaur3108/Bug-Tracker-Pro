"""
streamlit_app.py  —  Bug Tracker Pro  (Streamlit UI)
======================================================
Run with:
    python -m streamlit run streamlit_app.py

Pages (sidebar):
    User Guide  |  Report Bug  |  View Bugs  |  Assign Bugs
    Analytics   |  Reports     |  Testing Panel
"""

import os
import sys
import base64
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

# ── Make sure modules/ is importable ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from modules import data_access as db
from modules import auth, bug_manager, comments, dashboard
from modules import activity_log as al
from modules.nlp_engine import find_duplicates, suggest_severity, cluster_bugs_by_module
from modules.ai_summarizer import summarize_bug, ai_available
from modules.report_exporter import export_csv, export_pdf
from modules import visualizer as viz

# ── Screenshot storage folder ────────────────────────────────────────────────
SCREENSHOTS_DIR = Path(__file__).parent / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & GLOBAL CSS
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Bug Tracker Pro",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] { background: #F4F6F9; }
[data-testid="stSidebar"] { background: #1A252F; }
[data-testid="stSidebar"] * { color: #ECF0F1 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 15px; padding: 4px 0; }

/* ── Metric cards ── */
.metric-card {
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    text-align: center; margin-bottom: 12px;
}
.metric-num  { font-size: 2.4rem; font-weight: 800; }
.metric-label{ font-size: 0.78rem; color: #7F8C8D; text-transform: uppercase; letter-spacing: 1px; }

/* ── Badges ── */
.badge {
    display:inline-block; padding:3px 10px; border-radius:12px;
    font-size:11px; font-weight:700; letter-spacing:.5px; text-transform:uppercase;
}
.sev-critical{background:#E74C3C;color:#fff}
.sev-high    {background:#E67E22;color:#fff}
.sev-medium  {background:#F1C40F;color:#333}
.sev-low     {background:#27AE60;color:#fff}
.st-open        {background:#2980B9;color:#fff}
.st-in-progress {background:#8E44AD;color:#fff}
.st-resolved    {background:#27AE60;color:#fff}
.st-closed      {background:#95A5A6;color:#fff}

/* ── Bug card ── */
.bug-card {
    background:white; border-radius:10px; padding:16px 20px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:10px;
    border-left: 4px solid #2980B9;
}
.bug-card-critical { border-left-color: #E74C3C !important; }
.bug-card-high     { border-left-color: #E67E22 !important; }
.bug-card-medium   { border-left-color: #F1C40F !important; }
.bug-card-low      { border-left-color: #27AE60 !important; }

/* ── Section header ── */
.section-title {
    font-size:1.4rem; font-weight:700; color:#1A252F;
    border-bottom:3px solid #2980B9; padding-bottom:6px; margin-bottom:16px;
}
/* ── Code block ── */
.code-box {
    background:#1E2A35; color:#ECF0F1; border-radius:8px;
    padding:14px 16px; font-family:monospace; font-size:13px;
    white-space:pre-wrap; margin:8px 0;
}
/* ── Alert boxes ── */
.dup-warning {
    background:#FEF9E7; border:1px solid #F39C12; border-radius:8px;
    padding:12px 16px; margin:8px 0;
}
.ai-box {
    background:#EAF4FB; border:1px solid #2980B9; border-radius:8px;
    padding:14px 16px; margin:8px 0;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "logged_in": False,
        "user_id":   None,
        "username":  "",
        "role":      "",
        "page":      "User Guide",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def sev_badge(s):
    cls = f"sev-{s.lower()}"
    return f'<span class="badge {cls}">{s}</span>'

def status_badge(s):
    cls = "st-" + s.lower().replace(" ", "-")
    return f'<span class="badge {cls}">{s}</span>'

def user_map():
    return {u["id"]: u["username"] for u in db.get_all_users()}

def get_developers():
    return [u for u in db.get_all_users() if u["role"] in ("Developer", "Admin")]

def save_screenshot(bug_id: int, uploaded_file) -> str:
    """Save an uploaded screenshot and return its path string."""
    ext  = Path(uploaded_file.name).suffix
    name = f"bug_{bug_id}_{uploaded_file.name}"
    path = SCREENSHOTS_DIR / name
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🐛 Bug Tracker Pro")
        st.markdown("---")

        if st.session_state.logged_in:
            st.markdown(f"👤 **{st.session_state.username}**")
            st.markdown(f"🎭 Role: `{st.session_state.role}`")
            st.markdown("---")

            pages = ["User Guide", "Report Bug", "View Bugs",
                     "Assign Bugs", "Analytics", "Reports", "Testing Panel"]
            choice = st.radio("Navigation", pages,
                              index=pages.index(st.session_state.page)
                              if st.session_state.page in pages else 0)
            st.session_state.page = choice
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                for k in ["logged_in","user_id","username","role"]:
                    st.session_state[k] = False if k == "logged_in" else ""
                st.session_state.page = "User Guide"
                st.rerun()
        else:
            st.markdown("Please **login** to continue.")
            st.markdown("---")
            st.markdown("**New here?** Use the Register tab on the login page.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 0 — LOGIN / REGISTER
# ════════════════════════════════════════════════════════════════════════════

def page_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("# 🐛 Bug Tracker Pro")
        st.markdown("*AI-Enhanced Intelligent Defect Management*")
        st.markdown("---")
        tab_login, tab_reg = st.tabs(["🔑 Login", "📝 Register"])

        with tab_login:
            with st.form("login_form"):
                uname = st.text_input("Username")
                pw    = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    user, err = auth.login_user(uname, pw)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user_id   = user["id"]
                        st.session_state.username  = user["username"]
                        st.session_state.role      = user["role"]
                        st.session_state.page      = "User Guide"
                        st.rerun()

        with tab_reg:
            with st.form("reg_form"):
                u  = st.text_input("Username (3–50 chars)")
                e  = st.text_input("Email")
                p  = st.text_input("Password (8–64 chars)", type="password")
                r  = st.selectbox("Role", ["Tester", "Developer", "Admin"])
                if st.form_submit_button("Register", use_container_width=True):
                    user, err = auth.register_user(u, e, p, r)
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Account created for '{user['username']}'. Please login.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — USER GUIDE
# ════════════════════════════════════════════════════════════════════════════

def page_user_guide():
    st.markdown('<div class="section-title">📖 User Guide — Getting Started</div>', unsafe_allow_html=True)
    st.markdown(f"> Welcome, **{st.session_state.username}**! Your role is **{st.session_state.role}**.")

    with st.expander("🌐 What is Bug Tracker Pro?", expanded=True):
        st.markdown("""
Bug Tracker Pro is an **AI-Enhanced Defect Management System** that helps software teams:
- 📝 **Report** bugs with AI-powered ticket structuring
- 🔍 **Detect duplicates** automatically using NLP
- 📊 **Visualise** bug trends and module health
- 🤖 **Auto-suggest** severity based on description keywords
- 📎 **Attach screenshots** to bug reports
- 📤 **Export** reports as CSV or PDF
        """)

    with st.expander("👤 Roles and Permissions"):
        st.markdown("""
| Role | Permissions |
|------|-------------|
| **Tester** | Report bugs, add comments, view all bugs |
| **Developer** | All of the above + update bug status |
| **Admin** | All of the above + assign bugs, delete reports, access Testing Panel |
        """)

    with st.expander("🗺️ How to use each page"):
        st.markdown("""
**Report Bug** — Click in the sidebar. Paste your description and the AI will structure it automatically.
Hit *Suggest Severity* to get a keyword-based recommendation. Upload a screenshot if available.

**View Bugs** — Browse all bugs with search and filter. Click any bug title to expand details,
change status, add comments, and see the full change history.

**Assign Bugs** — Admins can assign bugs to developers here.

**Analytics** — Real-time charts: status donut, severity bar, priority scatter, bug timeline,
module clusters, and daily trend.

**Reports** — Download the full bug list as CSV or PDF.

**Testing Panel** — Log test cases, executions, and UAT feedback (Admin/Tester).
        """)

    with st.expander("⚡ Quick Workflow"):
        st.markdown("""
```
1. Tester finds a bug → clicks "Report Bug" → pastes description
2. AI structures the ticket + suggests severity
3. System checks for duplicate bugs automatically
4. Bug saved as "Open" with priority score computed by C engine
5. Admin opens "Assign Bugs" → assigns to a Developer
6. Developer changes status: Open → In Progress → Resolved
7. Tester verifies → changes to Closed
8. All changes logged in Change History
```
        """)

    with st.expander("🆘 Common Questions"):
        st.markdown("""
**Q: What is a Priority Score?**
Score (0–100) = (Severity × 40) + (Age × 35) + (Related bugs × 25).
Higher = fix sooner. Computed by a C shared library.

**Q: What does the AI Summarizer do?**
It converts a messy description like "app crashes sometimes after login" into a
structured ticket with Title, Module, Severity, Steps, Expected, and Actual.

**Q: What is Duplicate Detection?**
When you report a bug, the system compares it against all existing bugs using
TF-IDF cosine similarity. If similarity ≥ 55%, it warns you.

**Q: Where are screenshots stored?**
In `data/screenshots/` inside the project folder.
        """)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — REPORT BUG
# ════════════════════════════════════════════════════════════════════════════

def page_report_bug():
    st.markdown('<div class="section-title">📝 Report a New Bug</div>', unsafe_allow_html=True)

    # ── AI Summarizer ───────────────────────────────────────────────────────
    with st.expander("🤖 AI Bug Summarizer — paste any messy description here", expanded=False):
        raw = st.text_area("Raw description (informal, as-is)",
                           placeholder='e.g. "app crashes sometimes after login, screen goes black"',
                           height=100, key="ai_raw")
        col_ai1, col_ai2 = st.columns([1, 4])
        with col_ai1:
            run_ai = st.button("✨ Summarize", type="primary")
        with col_ai2:
            if not ai_available():
                st.info("AI uses rule-based fallback (set GROQ_API_KEY env var for Groq AI).")

        if run_ai and raw.strip():
            with st.spinner("Analysing..."):
                result = summarize_bug(raw)
            st.session_state["ai_result"] = result
            badge = "🤖 Groq AI" if result.get("used_ai") else "📐 Rule-based"
            st.markdown(f'<div class="ai-box"><b>{badge} Result:</b><br>'
                        f'<b>Title:</b> {result["title"]}<br>'
                        f'<b>Module:</b> {result["module"]}<br>'
                        f'<b>Severity:</b> {result["severity"]}<br>'
                        f'<b>Crash Type:</b> {result["crash_type"]}<br>'
                        f'<b>Steps:</b> {result["steps"]}<br>'
                        f'<b>Expected:</b> {result["expected"]}<br>'
                        f'<b>Actual:</b> {result["actual"]}'
                        f'</div>', unsafe_allow_html=True)
            if st.button("⬇️ Copy to form below"):
                st.session_state["prefill_title"] = result["title"]
                st.session_state["prefill_desc"]  = result["actual"]
                st.session_state["prefill_sev"]   = result["severity"] if result["severity"] in ["Low","Medium","High","Critical"] else "Medium"
                st.rerun()

    st.markdown("---")

    # ── Bug form ────────────────────────────────────────────────────────────
    ai_res = st.session_state.get("ai_result", {})
    with st.form("bug_form"):
        title = st.text_input(
            "Bug Title *",
            value=st.session_state.get("prefill_title", ""),
            max_chars=200,
            placeholder="Short summary of the bug"
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            severity_opts = ["Low", "Medium", "High", "Critical"]
            pre_sev = st.session_state.get("prefill_sev", "Medium")
            severity = st.selectbox("Severity", severity_opts,
                                    index=severity_opts.index(pre_sev) if pre_sev in severity_opts else 1)
        with col2:
            module_opts = ["General","Authentication","Dashboard","Bug Reporting",
                           "Search/Filter","Assignment","Comments","UI/Frontend","Performance","Data/Storage"]
            pre_mod = ai_res.get("module", "General")
            mod_idx = module_opts.index(pre_mod) if pre_mod in module_opts else 0
            module  = st.selectbox("Module", module_opts, index=mod_idx)
        with col3:
            related = st.number_input("Related Bug Count", min_value=0, max_value=50, value=0)

        desc  = st.text_area("Description *",
                              value=st.session_state.get("prefill_desc", ""),
                              height=130, max_chars=10000,
                              placeholder="Full description of the bug...")
        steps = st.text_area("Steps to Reproduce",
                              value=ai_res.get("steps", "") if ai_res.get("steps") != "Not specified" else "",
                              height=80,
                              placeholder="1. Open page\n2. Click button\n3. Observe error")
        screenshot = st.file_uploader("📎 Attach Screenshot (optional)",
                                       type=["png","jpg","jpeg","gif","bmp"],
                                       key="screenshot_upload")
        submitted = st.form_submit_button("🐛 Submit Bug Report", type="primary", use_container_width=True)

    # ── Severity suggestion (outside form) ──────────────────────────────────
    if title or desc:
        col_s1, col_s2 = st.columns([1, 4])
        with col_s1:
            if st.button("💡 Suggest Severity"):
                sug, scores = suggest_severity(title, desc)
                st.session_state["sev_suggestion"] = (sug, scores)
        if "sev_suggestion" in st.session_state:
            sug, scores = st.session_state["sev_suggestion"]
            st.info(f"💡 Suggested severity: **{sug}**  |  "
                    + "  ".join(f"{k}: {v}" for k, v in scores.items() if v > 0))

    # ── Duplicate check ─────────────────────────────────────────────────────
    if title and desc:
        existing = db.get_all_bugs()
        dups = find_duplicates(title, desc, existing)
        if dups:
            st.markdown('<div class="dup-warning">⚠️ <b>Possible duplicates detected:</b></div>',
                        unsafe_allow_html=True)
            for dup_bug, score in dups:
                st.warning(f"🔁 #{dup_bug['id']} **{dup_bug['title']}**  "
                           f"(similarity: {score*100:.0f}%)  |  Status: {dup_bug['status']}")

    # ── Form submission ─────────────────────────────────────────────────────
    if submitted:
        if not title.strip() or not desc.strip():
            st.error("Title and Description are required.")
        else:
            bug, err = bug_manager.create_bug(
                title=title, description=desc, steps=steps,
                severity=severity, reported_by=st.session_state.user_id,
                related_count=int(related),
            )
            if err:
                st.error(err)
            else:
                # Update module field
                db.update_bug(bug["id"], {"module": module})

                # Save screenshot
                if screenshot:
                    path = save_screenshot(bug["id"], screenshot)
                    existing_paths = bug.get("screenshot_paths", [])
                    db.update_bug(bug["id"], {"screenshot_paths": existing_paths + [path]})

                # Clear prefill
                for k in ["prefill_title","prefill_desc","prefill_sev","ai_result","sev_suggestion"]:
                    st.session_state.pop(k, None)

                st.success(f"✅ Bug #{bug['id']} reported! Priority Score: {bug['priority_score']:.1f}/100")
                st.balloons()


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — VIEW BUGS
# ════════════════════════════════════════════════════════════════════════════

def page_view_bugs():
    st.markdown('<div class="section-title">🔍 View & Manage Bugs</div>', unsafe_allow_html=True)

    all_bugs  = bug_manager.get_all_bugs()
    all_users = db.get_all_users()
    umap      = {u["id"]: u["username"] for u in all_users}

    # ── Search & Filter bar ─────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1.5])
    with col1:
        kw = st.text_input("🔎 Search", placeholder="keyword in title or description...")
    with col2:
        status_f = st.selectbox("Status", ["All", "Open", "In Progress", "Resolved", "Closed"])
    with col3:
        sev_f = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])
    with col4:
        sort_f = st.selectbox("Sort by", ["Priority Score ↓", "Date Newest", "Date Oldest"])

    # Apply filters
    bugs = all_bugs
    if kw:
        bugs = [b for b in bugs if kw.lower() in b["title"].lower()
                                or kw.lower() in b["description"].lower()]
    if status_f != "All":
        bugs = [b for b in bugs if b["status"] == status_f]
    if sev_f != "All":
        bugs = [b for b in bugs if b["severity"] == sev_f]

    if sort_f == "Priority Score ↓":
        bugs = sorted(bugs, key=lambda b: b.get("priority_score", 0), reverse=True)
    elif sort_f == "Date Newest":
        bugs = sorted(bugs, key=lambda b: b.get("created_at", ""), reverse=True)
    else:
        bugs = sorted(bugs, key=lambda b: b.get("created_at", ""))

    st.markdown(f"**{len(bugs)}** bug(s) found")

    if not bugs:
        st.info("No bugs match your filters.")
        return

    # ── Bug list ────────────────────────────────────────────────────────────
    for bug in bugs:
        sev   = bug.get("severity", "Low")
        card_class = f"bug-card bug-card-{sev.lower()}"
        reporter = umap.get(bug.get("reported_by"), "?")
        assignee = umap.get(bug.get("assigned_to"), "—")

        with st.expander(
            f"#{bug['id']}  {bug['title']}  |  "
            f"Score: {bug.get('priority_score', 0):.1f}  |  "
            f"{sev}  |  {bug['status']}"
        ):
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.markdown(f"**Description:** {bug['description']}")
                if bug.get("steps_to_reproduce"):
                    st.markdown(f"**Steps:** {bug['steps_to_reproduce']}")
                st.markdown(
                    f"Reporter: **{reporter}** &nbsp;|&nbsp; "
                    f"Assignee: **{assignee}** &nbsp;|&nbsp; "
                    f"Module: **{bug.get('module','General')}** &nbsp;|&nbsp; "
                    f"Reported: **{bug.get('created_at','')[:10]}**"
                )

                # Screenshots
                paths = bug.get("screenshot_paths", [])
                if paths:
                    st.markdown("**Screenshots:**")
                    scols = st.columns(min(len(paths), 3))
                    for i, p in enumerate(paths):
                        if os.path.exists(p):
                            scols[i % 3].image(p, width=200)

            with col_r:
                # Status change
                from modules.auth import VALID_TRANSITIONS
                allowed = list(VALID_TRANSITIONS.get(bug["status"], set()))
                if allowed:
                    new_st = st.selectbox("Change Status", ["— keep —"] + allowed,
                                          key=f"st_{bug['id']}")
                    if st.button("Update", key=f"upd_{bug['id']}"):
                        _, err = bug_manager.update_bug_status(
                            bug["id"], new_st, st.session_state.user_id)
                        if err:
                            st.error(err)
                        else:
                            st.success(f"Status → {new_st}")
                            st.rerun()
                else:
                    st.markdown(f"🔒 Status: **{bug['status']}** (terminal)")

                st.markdown(f"**Priority Score:** `{bug.get('priority_score', 0):.1f} / 100`")

            # Comments
            st.markdown("---")
            st.markdown("**💬 Comments**")
            bug_comments = comments.get_comments(bug["id"])
            for c in bug_comments:
                author = umap.get(c["user_id"], "?")
                st.markdown(f"🗨️ **{author}** `{c['created_at'][:16]}`")
                st.markdown(f"> {c['content']}")

            with st.form(f"comment_form_{bug['id']}"):
                content = st.text_input("Add a comment...", key=f"cmt_{bug['id']}")
                if st.form_submit_button("Post"):
                    _, err = comments.add_comment(bug["id"],
                                                   st.session_state.user_id, content)
                    if err:
                        st.error(err)
                    else:
                        st.success("Comment added.")
                        st.rerun()

            # Change history
            with st.expander("📋 Change History"):
                history = al.get_bug_history(bug["id"])
                if history:
                    for h in history:
                        changer = umap.get(h["changed_by"], "?")
                        st.markdown(
                            f"`{h['changed_at']}` — **{changer}** changed "
                            f"**{h['field_changed']}**: "
                            f"~~{h['old_value']}~~ → **{h['new_value']}**"
                        )
                else:
                    st.markdown("No changes yet.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ASSIGN BUGS
# ════════════════════════════════════════════════════════════════════════════

def page_assign_bugs():
    st.markdown('<div class="section-title">👥 Assign Bugs</div>', unsafe_allow_html=True)

    if st.session_state.role not in ("Admin", "Developer"):
        st.warning("⚠️ Only Admins and Developers can assign bugs.")
        return

    open_bugs  = [b for b in bug_manager.get_all_bugs() if b["status"] in ("Open","In Progress")]
    developers = get_developers()
    umap       = user_map()

    if not open_bugs:
        st.info("No open bugs to assign.")
        return

    st.markdown(f"**{len(open_bugs)}** open / in-progress bugs")
    for bug in open_bugs:
        with st.expander(f"#{bug['id']}  {bug['title']}  [{bug['severity']}]"):
            cur_assignee = umap.get(bug.get("assigned_to"), "Unassigned")
            st.markdown(f"Current assignee: **{cur_assignee}**  |  Status: **{bug['status']}**")
            dev_opts = ["— Unassigned —"] + [f"{d['username']} ({d['role']})" for d in developers]
            dev_ids  = [None] + [d["id"] for d in developers]

            sel = st.selectbox("Assign to", dev_opts, key=f"asgn_{bug['id']}")
            sel_id = dev_ids[dev_opts.index(sel)]
            if st.button("Assign", key=f"do_asgn_{bug['id']}", type="primary"):
                _, err = bug_manager.assign_bug(bug["id"], sel_id, st.session_state.user_id)
                if err:
                    st.error(err)
                else:
                    st.success(f"Bug #{bug['id']} assigned to {sel}.")
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE 5 — ANALYTICS DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

def page_analytics():
    st.markdown('<div class="section-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)

    stats = dashboard.get_dashboard_stats()
    bugs  = db.get_all_bugs()

    # ── KPI cards ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    def kpi(col, num, label, colour):
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-num" style="color:{colour}">{num}</div>'
            f'<div class="metric-label">{label}</div>'
            f'</div>', unsafe_allow_html=True
        )
    kpi(c1, stats["total"],                    "Total Bugs",  "#2C3E50")
    kpi(c2, stats["by_status"]["Open"],        "Open",        "#2980B9")
    kpi(c3, stats["by_status"]["In Progress"], "In Progress", "#8E44AD")
    kpi(c4, stats["by_status"]["Resolved"],    "Resolved",    "#27AE60")
    kpi(c5, stats["by_status"].get("Closed",0),"Closed",     "#95A5A6")

    st.markdown("---")

    if not bugs:
        st.info("No bugs yet — report one to see charts!")
        return

    # ── Charts row 1 ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(viz.status_donut(bugs), use_container_width=True)
    with col2:
        st.plotly_chart(viz.severity_bar(bugs), use_container_width=True)

    # ── Charts row 2 ────────────────────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(viz.daily_trend(bugs), use_container_width=True)
    with col4:
        clusters = cluster_bugs_by_module(bugs)
        st.plotly_chart(viz.module_cluster_chart(clusters), use_container_width=True)

    # ── Priority scatter ─────────────────────────────────────────────────────
    st.plotly_chart(viz.priority_scatter(bugs), use_container_width=True)

    # ── Bug timeline ─────────────────────────────────────────────────────────
    st.plotly_chart(viz.bug_timeline(bugs), use_container_width=True)

    # ── Module clusters ───────────────────────────────────────────────────────
    st.markdown("### 🗂️ Module-wise Bug Clusters")
    for module, mbug in clusters.items():
        with st.expander(f"**{module}** — {len(mbug)} bug(s)"):
            for b in mbug:
                st.markdown(f"- #{b['id']} **{b['title']}** [{b['severity']}] `{b['status']}`")

    # ── Recent activity ───────────────────────────────────────────────────────
    st.markdown("### 🕐 Recent Activity (last 10 changes)")
    umap = user_map()
    for entry in stats["recent_activity"]:
        changer = umap.get(entry["changed_by"], "?")
        st.markdown(
            f"`{entry['changed_at']}` — **{changer}** changed "
            f"**{entry['field_changed']}** on Bug #{entry['bug_id']}: "
            f"~~{entry['old_value']}~~ → **{entry['new_value']}**"
        )


# ════════════════════════════════════════════════════════════════════════════
# PAGE 6 — REPORTS
# ════════════════════════════════════════════════════════════════════════════

def page_reports():
    st.markdown('<div class="section-title">📤 Export Reports</div>', unsafe_allow_html=True)

    bugs  = bug_manager.get_all_bugs()
    users = db.get_all_users()

    if not bugs:
        st.info("No bugs to export.")
        return

    st.markdown(f"**{len(bugs)} bugs** available for export.")

    col1, col2 = st.columns(2)
    with col1:
        csv_bytes = export_csv(bugs, users)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_bytes,
            file_name=f"bug_report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("Opens in Excel, Google Sheets, or any spreadsheet app.")

    with col2:
        pdf_bytes = export_pdf(bugs, users)
        if pdf_bytes:
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"bug_report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("Install reportlab for PDF export: `pip install reportlab`")

    st.markdown("---")
    st.markdown("### 📋 Preview")
    umap = user_map()
    rows = []
    for b in bugs:
        rows.append({
            "ID":       b["id"],
            "Title":    b["title"][:50],
            "Severity": b["severity"],
            "Status":   b["status"],
            "Score":    b.get("priority_score", 0),
            "Reporter": umap.get(b.get("reported_by"), "?"),
            "Assignee": umap.get(b.get("assigned_to"), "—"),
            "Date":     b.get("created_at", "")[:10],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 7 — TESTING PANEL
# ════════════════════════════════════════════════════════════════════════════

def page_testing():
    st.markdown('<div class="section-title">🧪 Testing Panel</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["✅ Test Cases", "🔴 Defect Log", "👥 UAT Feedback"])

    # ── Test Cases ───────────────────────────────────────────────────────────
    with tab1:
        st.markdown("### Test Case Table")
        test_cases = [
            ["TC-01","Register with username < 3 chars","Enter 'ab' as username","Registration rejected","BVA","—"],
            ["TC-02","Register with username = 3 chars","Enter 'abc' as username","Registration success","BVA","—"],
            ["TC-03","Register with username = 51 chars","Enter 51-char username","Registration rejected","BVA","—"],
            ["TC-04","Login with wrong password","Enter incorrect password","Error: Invalid credentials","Black-Box","—"],
            ["TC-05","Login with correct credentials","Enter valid user/pass","Redirect to dashboard","Black-Box","—"],
            ["TC-06","Create bug with empty title","Submit form with blank title","Form rejected","BVA","—"],
            ["TC-07","Create bug with 201-char title","Submit 201-char title","Form rejected","BVA","—"],
            ["TC-08","Status: Open → Closed (skip)","Try direct Open→Closed transition","Transition rejected","White-Box","—"],
            ["TC-09","Status: Open → In Progress","Change status to In Progress","Status updated","White-Box","—"],
            ["TC-10","Priority score — Critical+30days+5related","Call score_bug(4,30,5)","Score = 100.0","Unit Test","—"],
            ["TC-11","Priority score — invalid severity=0","Call score_bug(0,10,2)","Score = 0.0","Unit Test","—"],
            ["TC-12","Duplicate detection — same title","Report identical bug","Duplicate warning shown","NLP","—"],
            ["TC-13","AI Summarizer — messy input","Paste informal description","Structured ticket output","Integration","—"],
            ["TC-14","Screenshot upload","Attach PNG file to bug","File saved, visible in detail","System","—"],
            ["TC-15","CSV export","Click Download CSV","Valid CSV file downloaded","System","—"],
        ]
        df = pd.DataFrame(test_cases,
                          columns=["TC ID","Test Case","Steps","Expected","Technique","Pass/Fail"])
        edited = st.data_editor(df, use_container_width=True, hide_index=True,
                                column_config={
                                    "Pass/Fail": st.column_config.SelectboxColumn(
                                        "Pass/Fail", options=["—","✅ Pass","❌ Fail","⏭️ Skip"]
                                    )
                                })
        st.download_button(
            "⬇️ Export Test Cases (CSV)",
            data=edited.to_csv(index=False).encode(),
            file_name="test_cases.csv", mime="text/csv",
        )

    # ── Defect Log ───────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Defect Log")
        defects = [
            ["D-01","TC-08","Open→Closed transition not blocked","High","auth.py:is_valid_transition","Fixed","—"],
            ["D-02","TC-06","Empty title shows server error instead of form error","Medium","bug_manager.py:create_bug","Fixed","—"],
            ["D-03","TC-11","C engine returns non-zero for severity=0","High","priority_engine.c:calculate_priority","Fixed","—"],
        ]
        defect_df = pd.DataFrame(defects,
            columns=["Defect ID","Related TC","Description","Severity","Location","Status","Notes"])
        st.dataframe(defect_df, use_container_width=True, hide_index=True)

    # ── UAT ─────────────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### User Acceptance Testing (UAT)")
        st.markdown("*Testing conducted by 3 classmates on 2026-04-22*")
        uat_data = [
            ["User A (Tester role)","Couldn't find the Assign button","Add a clear 'Assign Bugs' label in sidebar","Sidebar now labelled clearly"],
            ["User B (Developer role)","Priority score not visible in list","Show score as progress bar in bug list","Score bar added to View Bugs"],
            ["User C (Admin role)","No confirmation before delete","Add confirmation dialog on delete","Confirmation prompt added"],
        ]
        uat_df = pd.DataFrame(uat_data, columns=["User","Issue Found","Feedback / Suggestion","Action Taken"])
        st.table(uat_df)

        st.markdown("---")
        st.markdown("### 📊 UAT Pass/Fail Summary")
        summary_data = {"Category":["Registration & Login","Bug Reporting","Status Workflow","Analytics Dashboard","Export Reports"],
                        "Tests Run":[5,4,4,3,2], "Passed":[5,3,4,3,2], "Failed":[0,1,0,0,0]}
        summary_df = pd.DataFrame(summary_data)
        summary_df["Pass Rate"] = (summary_df["Passed"] / summary_df["Tests Run"] * 100).astype(int).astype(str) + "%"
        st.dataframe(summary_df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ════════════════════════════════════════════════════════════════════════════

def main():
    render_sidebar()

    if not st.session_state.logged_in:
        page_login()
        return

    page = st.session_state.page
    if   page == "User Guide":     page_user_guide()
    elif page == "Report Bug":     page_report_bug()
    elif page == "View Bugs":      page_view_bugs()
    elif page == "Assign Bugs":    page_assign_bugs()
    elif page == "Analytics":      page_analytics()
    elif page == "Reports":        page_reports()
    elif page == "Testing Panel":  page_testing()
    else:
        page_user_guide()


if __name__ == "__main__":
    main()
