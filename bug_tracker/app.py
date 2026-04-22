"""
app.py  —  Bug Tracker Flask Application
==========================================
Entry point for the Bug Tracker web application.

Architecture
------------
    Presentation  : Jinja2 templates (templates/)
    Application   : This file (Flask routes) + modules/
    Data          : JSON files (data/)
    Priority Eng. : C shared library called via ctypes (modules/priority.py)

Routes
------
    GET  /                    → redirect to /dashboard or /login
    GET  /register            → registration form
    POST /register            → create account
    GET  /login               → login form
    POST /login               → authenticate
    GET  /logout              → end session
    GET  /dashboard           → summary stats
    GET  /bugs                → filtered bug list
    GET  /bugs/new            → create-bug form
    POST /bugs/new            → submit new bug
    GET  /bugs/<id>           → bug detail + comments + history
    GET  /bugs/<id>/edit      → edit-bug form
    POST /bugs/<id>/edit      → submit edits
    POST /bugs/<id>/status    → change lifecycle status
    POST /bugs/<id>/assign    → assign to developer
    POST /bugs/<id>/comment   → post a comment
    POST /bugs/<id>/delete    → delete bug (Admin only)

Run
---
    python app.py
    Then open http://127.0.0.1:5000
"""

import functools
import os

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from modules import auth, bug_manager, comments, dashboard, search_filter
from modules import activity_log as al
from modules import data_access as db

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
# Secret key is required for Flask sessions; use an env var in production
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-in-production")


# ---------------------------------------------------------------------------
# Session / access-control helpers
# ---------------------------------------------------------------------------

def login_required(view):
    """Decorator: redirect to /login if the user is not authenticated."""
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    """Decorator: return 403 unless the current user has the Admin role."""
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") != "Admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard_view"))
        return view(*args, **kwargs)
    return login_required(wrapper)


def current_user() -> dict | None:
    """Return the logged-in user's record, or None."""
    uid = session.get("user_id")
    return db.get_user_by_id(uid) if uid else None


# Make current_user available to every template automatically
@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard_view"))
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Authentication routes
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """Display and process the user-registration form."""
    if request.method == "POST":
        user, error = auth.register_user(
            username=request.form.get("username", ""),
            email=request.form.get("email", ""),
            password=request.form.get("password", ""),
            role=request.form.get("role", "Tester"),
        )
        if error:
            flash(error, "danger")
            return render_template("register.html")
        flash(f"Account created for '{user['username']}'. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Display and process the login form."""
    if "user_id" in session:
        return redirect(url_for("dashboard_view"))

    if request.method == "POST":
        user, error = auth.login_user(
            username=request.form.get("username", ""),
            password=request.form.get("password", ""),
        )
        if error:
            flash(error, "danger")
            return render_template("login.html")

        # Store minimal session data — never store passwords or hashes
        session["user_id"]  = user["id"]
        session["username"] = user["username"]
        session["role"]     = user["role"]
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(url_for("dashboard_view"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Clear the session and redirect to the login page."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard_view():
    """Render the main summary dashboard."""
    stats = dashboard.get_dashboard_stats()
    # Attach username to each recent activity entry for display
    all_users = {u["id"]: u["username"] for u in db.get_all_users()}
    for entry in stats["recent_activity"]:
        entry["changer_name"] = all_users.get(entry["changed_by"], "Unknown")
    return render_template("dashboard.html", stats=stats)


# ---------------------------------------------------------------------------
# Bug list
# ---------------------------------------------------------------------------

@app.route("/bugs")
@login_required
def bug_list():
    """Display a filterable, searchable list of bugs."""
    keyword     = request.args.get("q", "").strip()
    status      = request.args.get("status", "")
    severity    = request.args.get("severity", "")
    sort_by     = request.args.get("sort", "priority_score")
    ascending   = request.args.get("asc", "0") == "1"

    bugs = search_filter.search_bugs(
        keyword=keyword,
        status=status,
        severity=severity,
        sort_by=sort_by,
        ascending=ascending,
    )

    # Attach reporter username for display
    all_users = {u["id"]: u["username"] for u in db.get_all_users()}
    for bug in bugs:
        bug["reporter_name"] = all_users.get(bug["reported_by"], "Unknown")
        bug["assignee_name"] = all_users.get(bug["assigned_to"], "—") if bug["assigned_to"] else "—"

    return render_template(
        "bug_list.html",
        bugs=bugs,
        keyword=keyword,
        status=status,
        severity=severity,
        sort_by=sort_by,
        ascending=ascending,
    )


# ---------------------------------------------------------------------------
# Create bug
# ---------------------------------------------------------------------------

@app.route("/bugs/new", methods=["GET", "POST"])
@login_required
def bug_create():
    """Display and process the new-bug form."""
    if request.method == "POST":
        bug, error = bug_manager.create_bug(
            title=request.form.get("title", ""),
            description=request.form.get("description", ""),
            steps=request.form.get("steps", ""),
            severity=request.form.get("severity", "Medium"),
            reported_by=session["user_id"],
            related_count=int(request.form.get("related_count", 0) or 0),
        )
        if error:
            flash(error, "danger")
            return render_template("bug_create.html")
        flash(f"Bug #{bug['id']} reported successfully.", "success")
        return redirect(url_for("bug_detail", bug_id=bug["id"]))

    return render_template("bug_create.html")


# ---------------------------------------------------------------------------
# Bug detail
# ---------------------------------------------------------------------------

@app.route("/bugs/<int:bug_id>")
@login_required
def bug_detail(bug_id: int):
    """Display a single bug with comments, activity history, and action forms."""
    bug = bug_manager.get_bug(bug_id)
    if bug is None:
        flash("Bug not found.", "warning")
        return redirect(url_for("bug_list"))

    all_users    = {u["id"]: u for u in db.get_all_users()}
    developers   = [u for u in db.get_all_users() if u["role"] in ("Developer", "Admin")]
    bug_comments = comments.get_comments(bug_id)
    history      = al.get_bug_history(bug_id)

    # Attach usernames to comments and history for display
    for c in bug_comments:
        c["author_name"] = all_users.get(c["user_id"], {}).get("username", "Unknown")
    for h in history:
        h["changer_name"] = all_users.get(h["changed_by"], {}).get("username", "Unknown")

    reporter = all_users.get(bug["reported_by"], {})
    assignee = all_users.get(bug["assigned_to"], {}) if bug["assigned_to"] else None

    from modules.auth import VALID_TRANSITIONS
    allowed_next = list(VALID_TRANSITIONS.get(bug["status"], set()))

    return render_template(
        "bug_detail.html",
        bug=bug,
        reporter=reporter,
        assignee=assignee,
        comments=bug_comments,
        history=history,
        developers=developers,
        allowed_next=allowed_next,
    )


# ---------------------------------------------------------------------------
# Edit bug
# ---------------------------------------------------------------------------

@app.route("/bugs/<int:bug_id>/edit", methods=["GET", "POST"])
@login_required
def bug_edit(bug_id: int):
    """Display and process the edit-bug form."""
    bug = bug_manager.get_bug(bug_id)
    if bug is None:
        flash("Bug not found.", "warning")
        return redirect(url_for("bug_list"))

    if request.method == "POST":
        updated, error = bug_manager.edit_bug(
            bug_id=bug_id,
            title=request.form.get("title", ""),
            description=request.form.get("description", ""),
            steps=request.form.get("steps", ""),
            severity=request.form.get("severity", bug["severity"]),
            changed_by=session["user_id"],
        )
        if error:
            flash(error, "danger")
            return render_template("bug_edit.html", bug=bug)
        flash("Bug updated.", "success")
        return redirect(url_for("bug_detail", bug_id=bug_id))

    return render_template("bug_edit.html", bug=bug)


# ---------------------------------------------------------------------------
# Status transition
# ---------------------------------------------------------------------------

@app.route("/bugs/<int:bug_id>/status", methods=["POST"])
@login_required
def bug_status(bug_id: int):
    """Process a status-change form submission."""
    new_status = request.form.get("status", "")
    _, error = bug_manager.update_bug_status(bug_id, new_status, session["user_id"])
    if error:
        flash(error, "danger")
    else:
        flash(f"Status changed to '{new_status}'.", "success")
    return redirect(url_for("bug_detail", bug_id=bug_id))


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

@app.route("/bugs/<int:bug_id>/assign", methods=["POST"])
@login_required
def bug_assign(bug_id: int):
    """Process a bug-assignment form submission. Admin-only in production."""
    raw = request.form.get("developer_id", "")
    developer_id = int(raw) if raw.isdigit() else None
    _, error = bug_manager.assign_bug(bug_id, developer_id, session["user_id"])
    if error:
        flash(error, "danger")
    else:
        flash("Assignment updated.", "success")
    return redirect(url_for("bug_detail", bug_id=bug_id))


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------

@app.route("/bugs/<int:bug_id>/comment", methods=["POST"])
@login_required
def bug_comment(bug_id: int):
    """Add a comment to a bug report."""
    content = request.form.get("content", "")
    _, error = comments.add_comment(bug_id, session["user_id"], content)
    if error:
        flash(error, "danger")
    else:
        flash("Comment added.", "success")
    return redirect(url_for("bug_detail", bug_id=bug_id))


# ---------------------------------------------------------------------------
# Delete bug
# ---------------------------------------------------------------------------

@app.route("/bugs/<int:bug_id>/delete", methods=["POST"])
@admin_required
def bug_delete(bug_id: int):
    """Permanently delete a bug report. Restricted to Admin users."""
    success, error = bug_manager.delete_bug(bug_id)
    if error:
        flash(error, "danger")
        return redirect(url_for("bug_detail", bug_id=bug_id))
    flash(f"Bug #{bug_id} deleted.", "success")
    return redirect(url_for("bug_list"))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # debug=True enables auto-reload and the Werkzeug debugger.
    # Never use debug=True in a production deployment.
    app.run(debug=True, port=5000)
