"""
modules/activity_log.py  —  Activity Log Module
=================================================
Read-only interface to the audit trail for a single bug.
Write operations are handled internally by data_access.log_activity(),
which is called by bug_manager after every mutating operation.
"""

from modules import data_access as db


def get_bug_history(bug_id: int) -> list:
    """
    Return all activity log entries for a bug, newest-first.

    :param bug_id: ID of the bug whose history to retrieve.
    :return:       List of activity log dictionaries sorted by changed_at descending.
    """
    entries = db.get_activity_for_bug(bug_id)
    return sorted(entries, key=lambda e: e["changed_at"], reverse=True)
