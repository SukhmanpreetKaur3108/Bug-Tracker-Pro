"""
modules/bug_manager.py  —  Bug Management Module
=================================================
Core CRUD operations and lifecycle management for bug reports.

Severity levels (stored as strings):
    Low | Medium | High | Critical

Status workflow (enforced via auth.is_valid_transition):
    Open → In Progress → Resolved → Closed

Priority score is computed by the C priority engine immediately on bug
creation (or after an edit) and persisted so the list view can sort
by urgency without re-computing every request.

Field length limits (match the BVA test boundaries in the test plan):
    Title       : 1 – 200 characters
    Description : 1 – 10 000 characters
"""

from datetime import datetime

from modules import data_access as db
from modules.auth import is_valid_transition
from modules.priority import score_bug

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps human-readable severity to the integer expected by the C engine
SEVERITY_MAP: dict[str, int] = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
VALID_SEVERITIES = set(SEVERITY_MAP.keys())

VALID_STATUSES = {"Open", "In Progress", "Resolved", "Closed"}

MAX_TITLE_LEN = 200
MAX_DESC_LEN  = 10_000


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_bug(
    title: str,
    description: str,
    steps: str,
    severity: str,
    reported_by: int,
    related_count: int = 0,
) -> tuple[dict | None, str | None]:
    """
    Validate inputs and persist a new bug report.

    The priority_score is computed immediately using severity, age = 0 days
    (just reported), and the supplied related_count.

    :param title:         Short bug summary (1–200 chars).
    :param description:   Full description (1–10 000 chars).
    :param steps:         Steps to reproduce (optional free text).
    :param severity:      One of Low / Medium / High / Critical.
    :param reported_by:   ID of the user filing the report.
    :param related_count: Known number of related bugs (default 0).
    :return:              (bug_dict, None) on success; (None, error_message) on failure.
    """
    title       = title.strip()
    description = description.strip()

    if not (1 <= len(title) <= MAX_TITLE_LEN):
        return None, f"Title must be between 1 and {MAX_TITLE_LEN} characters."
    if not (1 <= len(description) <= MAX_DESC_LEN):
        return None, f"Description must be between 1 and {MAX_DESC_LEN} characters."
    if severity not in VALID_SEVERITIES:
        return None, f"Severity must be one of: {', '.join(sorted(VALID_SEVERITIES))}."
    if related_count < 0:
        return None, "related_count must be >= 0."

    priority_score = score_bug(SEVERITY_MAP[severity], age_days=0, related_count=related_count)
    priority_label = _score_to_label(priority_score)

    bug = db.create_bug({
        "title":              title,
        "description":        description,
        "steps_to_reproduce": steps.strip(),
        "severity":           severity,
        "priority":           priority_label,
        "priority_score":     round(priority_score, 2),
        "reported_by":        reported_by,
    })
    return bug, None


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_bug(bug_id: int) -> dict | None:
    """Return a single bug by ID, or None if not found."""
    return db.get_bug_by_id(bug_id)


def get_all_bugs() -> list:
    """Return all bugs sorted by priority_score descending (most urgent first)."""
    return sorted(
        db.get_all_bugs(),
        key=lambda b: b.get("priority_score", 0.0),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Update — status transition
# ---------------------------------------------------------------------------

def update_bug_status(
    bug_id: int,
    new_status: str,
    changed_by: int,
) -> tuple[dict | None, str | None]:
    """
    Transition a bug to a new lifecycle status, enforcing the valid-transition rules.

    Allowed transitions:
        Open        → In Progress
        In Progress → Resolved | Open
        Resolved    → Closed   | In Progress
        Closed      → (terminal)

    Cyclomatic complexity  V(G) = 4:
        1. Bug not found
        2. Invalid status string
        3. Invalid transition
        4. Success

    :param bug_id:     ID of the bug.
    :param new_status: Desired next status.
    :param changed_by: ID of the user requesting the transition.
    :return:           (updated_bug, None) on success; (None, error_message) on failure.
    """
    bug = db.get_bug_by_id(bug_id)
    if bug is None:
        return None, "Bug not found."
    if new_status not in VALID_STATUSES:
        return None, f"'{new_status}' is not a valid status."
    if not is_valid_transition(bug["status"], new_status):
        return None, (
            f"Cannot transition from '{bug['status']}' to '{new_status}'. "
            "Check the allowed workflow."
        )

    old_status = bug["status"]
    updated    = db.update_bug(bug_id, {"status": new_status})
    db.log_activity(bug_id, changed_by, "status", old_status, new_status)
    return updated, None


# ---------------------------------------------------------------------------
# Update — assignment
# ---------------------------------------------------------------------------

def assign_bug(
    bug_id: int,
    developer_id: int | None,
    assigned_by: int,
) -> tuple[dict | None, str | None]:
    """
    Assign a bug to a developer (or clear the assignment with developer_id=None).

    :param bug_id:       ID of the bug.
    :param developer_id: ID of the developer, or None to unassign.
    :param assigned_by:  ID of the admin / lead performing the assignment.
    :return:             (updated_bug, None) on success; (None, error_message) on failure.
    """
    bug = db.get_bug_by_id(bug_id)
    if bug is None:
        return None, "Bug not found."

    old_val = str(bug.get("assigned_to"))
    updated = db.update_bug(bug_id, {"assigned_to": developer_id})
    db.log_activity(bug_id, assigned_by, "assigned_to", old_val, str(developer_id))
    return updated, None


# ---------------------------------------------------------------------------
# Update — full edit
# ---------------------------------------------------------------------------

def edit_bug(
    bug_id: int,
    title: str,
    description: str,
    steps: str,
    severity: str,
    changed_by: int,
) -> tuple[dict | None, str | None]:
    """
    Edit the core descriptive fields of an existing bug report.

    Re-computes priority_score using the bug's current age so the score
    reflects real time elapsed since the bug was first reported.

    :param bug_id:      ID of the bug to edit.
    :param title:       New title (1–200 chars).
    :param description: New description (1–10 000 chars).
    :param steps:       New steps-to-reproduce (optional).
    :param severity:    New severity (Low / Medium / High / Critical).
    :param changed_by:  ID of the user making the edit.
    :return:            (updated_bug, None) on success; (None, error_message) on failure.
    """
    bug = db.get_bug_by_id(bug_id)
    if bug is None:
        return None, "Bug not found."

    title       = title.strip()
    description = description.strip()

    if not (1 <= len(title) <= MAX_TITLE_LEN):
        return None, f"Title must be between 1 and {MAX_TITLE_LEN} characters."
    if not (1 <= len(description) <= MAX_DESC_LEN):
        return None, f"Description must be between 1 and {MAX_DESC_LEN} characters."
    if severity not in VALID_SEVERITIES:
        return None, f"Severity must be one of: {', '.join(sorted(VALID_SEVERITIES))}."

    # Compute age of the bug in days for an updated priority score
    created  = datetime.strptime(bug["created_at"], "%Y-%m-%dT%H:%M:%S")
    age_days = max((datetime.utcnow() - created).days, 0)

    priority_score = score_bug(SEVERITY_MAP[severity], age_days=age_days, related_count=0)
    priority_label = _score_to_label(priority_score)

    updated = db.update_bug(bug_id, {
        "title":              title,
        "description":        description,
        "steps_to_reproduce": steps.strip(),
        "severity":           severity,
        "priority":           priority_label,
        "priority_score":     round(priority_score, 2),
    })
    db.log_activity(bug_id, changed_by, "edit", "—", f"Fields edited by user {changed_by}")
    return updated, None


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_bug(bug_id: int) -> tuple[bool, str | None]:
    """
    Permanently delete a bug report and its activity log entries.

    Access control (Admin-only) must be enforced at the route layer.

    :param bug_id: ID of the bug to delete.
    :return:       (True, None) on success; (False, error_message) on failure.
    """
    if db.get_bug_by_id(bug_id) is None:
        return False, "Bug not found."
    db.delete_bug(bug_id)
    return True, None


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _score_to_label(score: float) -> str:
    """
    Map a numeric priority score (0–100) to a human-readable label.

        score >= 75  →  Critical
        score >= 50  →  High
        score >= 25  →  Medium
        score  < 25  →  Low
    """
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"
