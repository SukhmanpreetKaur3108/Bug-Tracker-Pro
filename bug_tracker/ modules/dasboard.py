"""
modules/dashboard.py  —  Dashboard Statistics Module
======================================================
Aggregates bug counts by status and severity for the main dashboard view.
All computation is performed in memory over the JSON data so no queries
are needed.
"""

from collections import Counter
from modules import data_access as db


def get_dashboard_stats() -> dict:
    """
    Compute a summary of bug statistics across the whole project.

    :return: A dictionary with the following keys:

        total           (int)  — total number of bug reports
        by_status       (dict) — {status: count} for all four statuses
        by_severity     (dict) — {severity: count} for all four severities
        recent_activity (list) — last 10 audit-log entries, newest first
        open_count      (int)  — shortcut: number of Open bugs
    """
    bugs = db.get_all_bugs()

    by_status   = Counter(b["status"]   for b in bugs)
    by_severity = Counter(b["severity"] for b in bugs)

    # Ensure every expected key is present even when its count is zero
    for status in ("Open", "In Progress", "Resolved", "Closed"):
        by_status.setdefault(status, 0)
    for sev in ("Low", "Medium", "High", "Critical"):
        by_severity.setdefault(sev, 0)

    all_logs        = db.get_all_activity_log()
    recent_activity = sorted(all_logs, key=lambda e: e["changed_at"], reverse=True)[:10]

    return {
        "total":           len(bugs),
        "by_status":       dict(by_status),
        "by_severity":     dict(by_severity),
        "recent_activity": recent_activity,
        "open_count":      by_status["Open"],
    }
