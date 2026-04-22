"""
modules/data_access.py  —  JSON Data Access Layer
===================================================
All read / write operations on the four JSON storage files are routed
through this module.  A threading.RLock serialises concurrent accesses
so the Flask dev-server (which can spawn threads) cannot corrupt data.

Files managed
-------------
    data/users.json          user accounts
    data/bugs.json           bug reports
    data/comments.json       per-bug comments
    data/activity_log.json   audit trail of every change
"""

import json
import os
import threading
from datetime import datetime

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

_FILES = {
    "users":        os.path.join(_BASE_DIR, "users.json"),
    "bugs":         os.path.join(_BASE_DIR, "bugs.json"),
    "comments":     os.path.join(_BASE_DIR, "comments.json"),
    "activity_log": os.path.join(_BASE_DIR, "activity_log.json"),
}

# Root key used in each file (must match the key in _FILES)
_ROOT_KEYS = {
    "users":        "users",
    "bugs":         "bugs",
    "comments":     "comments",
    "activity_log": "logs",
}

# One re-entrant lock shared by every function to prevent data races
_lock = threading.RLock()


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _ensure_file(path: str, root_key: str) -> None:
    """Create a JSON file with an empty list if it does not exist yet."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({root_key: []}, fh, indent=2)


def _load(store: str) -> dict:
    """Load and return the full contents of a JSON store."""
    path = _FILES[store]
    root = _ROOT_KEYS[store]
    _ensure_file(path, root)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(store: str, data: dict) -> None:
    """
    Write data back to a JSON file using a write-then-rename pattern.
    The rename is atomic on most operating systems and prevents a crash
    from leaving a half-written file.
    """
    path = _FILES[store]
    tmp  = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _next_id(records: list) -> int:
    """Return max(existing ids) + 1, or 1 if the list is empty."""
    return max((r["id"] for r in records), default=0) + 1


def _now() -> str:
    """Current UTC time as ISO 8601 string (no timezone suffix)."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

def get_all_users() -> list:
    """Return the full list of user records."""
    with _lock:
        return _load("users")["users"]


def get_user_by_id(user_id: int) -> dict | None:
    """Return the user record with the given ID, or None."""
    with _lock:
        return next(
            (u for u in _load("users")["users"] if u["id"] == user_id),
            None,
        )


def get_user_by_username(username: str) -> dict | None:
    """Return the user record with the given username (case-sensitive), or None."""
    with _lock:
        return next(
            (u for u in _load("users")["users"] if u["username"] == username),
            None,
        )


def create_user(username: str, email: str, password_hash: str, role: str) -> dict:
    """
    Append a new user record to users.json and return it.

    :param username:      Unique display name.
    :param email:         User's email address.
    :param password_hash: bcrypt hash of the plaintext password.
    :param role:          One of 'Admin', 'Developer', 'Tester'.
    """
    with _lock:
        store = _load("users")
        user = {
            "id":            _next_id(store["users"]),
            "username":      username,
            "email":         email,
            "password_hash": password_hash,
            "role":          role,
            "created_at":    _now(),
        }
        store["users"].append(user)
        _save("users", store)
        return user


# ---------------------------------------------------------------------------
# Bug operations
# ---------------------------------------------------------------------------

def get_all_bugs() -> list:
    """Return all bug records (unsorted)."""
    with _lock:
        return _load("bugs")["bugs"]


def get_bug_by_id(bug_id: int) -> dict | None:
    """Return the bug record with the given ID, or None."""
    with _lock:
        return next(
            (b for b in _load("bugs")["bugs"] if b["id"] == bug_id),
            None,
        )


def create_bug(data: dict) -> dict:
    """
    Append a new bug record to bugs.json and return it.

    Expected keys in *data*:
        title, description, steps_to_reproduce, severity, priority,
        priority_score, reported_by
    """
    with _lock:
        store = _load("bugs")
        ts = _now()
        bug = {
            "id":                 _next_id(store["bugs"]),
            "title":              data["title"],
            "description":        data["description"],
            "steps_to_reproduce": data.get("steps_to_reproduce", ""),
            "severity":           data["severity"],
            "priority":           data["priority"],
            "priority_score":     data.get("priority_score", 0.0),
            "status":             "Open",
            "reported_by":        data["reported_by"],
            "assigned_to":        None,
            "module":             data.get("module", "General"),
            "screenshot_paths":   data.get("screenshot_paths", []),
            "created_at":         ts,
            "updated_at":         ts,
        }
        store["bugs"].append(bug)
        _save("bugs", store)
        return bug


def update_bug(bug_id: int, updates: dict) -> dict | None:
    """
    Apply a dict of field updates to the bug with the given ID.

    :param bug_id:  ID of the bug to update.
    :param updates: Mapping of field_name → new_value.
    :return:        The updated bug record, or None if the ID was not found.
    """
    with _lock:
        store = _load("bugs")
        for bug in store["bugs"]:
            if bug["id"] == bug_id:
                bug.update(updates)
                bug["updated_at"] = _now()
                _save("bugs", store)
                return bug
        return None


def delete_bug(bug_id: int) -> bool:
    """
    Remove the bug record with the given ID.

    :return: True if a record was deleted; False if the ID was not found.
    """
    with _lock:
        store = _load("bugs")
        before = len(store["bugs"])
        store["bugs"] = [b for b in store["bugs"] if b["id"] != bug_id]
        if len(store["bugs"]) < before:
            _save("bugs", store)
            return True
        return False


# ---------------------------------------------------------------------------
# Comment operations
# ---------------------------------------------------------------------------

def get_comments_for_bug(bug_id: int) -> list:
    """Return all comments for the specified bug (unsorted)."""
    with _lock:
        return [c for c in _load("comments")["comments"] if c["bug_id"] == bug_id]


def create_comment(bug_id: int, user_id: int, content: str) -> dict:
    """
    Append a new comment to comments.json and return it.

    :param bug_id:  ID of the bug being commented on.
    :param user_id: ID of the user posting the comment.
    :param content: Comment body text.
    """
    with _lock:
        store = _load("comments")
        comment = {
            "id":         _next_id(store["comments"]),
            "bug_id":     bug_id,
            "user_id":    user_id,
            "content":    content,
            "created_at": _now(),
        }
        store["comments"].append(comment)
        _save("comments", store)
        return comment


# ---------------------------------------------------------------------------
# Activity log operations
# ---------------------------------------------------------------------------

def log_activity(
    bug_id: int,
    changed_by: int,
    field: str,
    old_val: str,
    new_val: str,
) -> dict:
    """
    Append an audit entry to activity_log.json and return it.

    :param bug_id:     ID of the affected bug.
    :param changed_by: ID of the user making the change.
    :param field:      Name of the field that changed.
    :param old_val:    Previous value (as a string).
    :param new_val:    New value (as a string).
    """
    with _lock:
        store = _load("activity_log")
        entry = {
            "id":            _next_id(store["logs"]),
            "bug_id":        bug_id,
            "changed_by":    changed_by,
            "field_changed": field,
            "old_value":     old_val,
            "new_value":     new_val,
            "changed_at":    _now(),
        }
        store["logs"].append(entry)
        _save("activity_log", store)
        return entry


def get_activity_for_bug(bug_id: int) -> list:
    """Return all activity log entries for the specified bug (unsorted)."""
    with _lock:
        return [e for e in _load("activity_log")["logs"] if e["bug_id"] == bug_id]


def get_all_activity_log() -> list:
    """Return every activity log entry across all bugs (unsorted)."""
    with _lock:
        return _load("activity_log")["logs"]
