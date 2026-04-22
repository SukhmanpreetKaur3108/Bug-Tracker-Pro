"""
modules/search_filter.py  —  Search and Filter Module
======================================================
Provides keyword search and multi-criteria filtering over the in-memory
bug list.  All filtering is done in Python so no external query language
is required.
"""

from modules import data_access as db


def search_bugs(
    keyword: str = "",
    status: str = "",
    severity: str = "",
    assignee_id: int | None = None,
    sort_by: str = "priority_score",
    ascending: bool = False,
) -> list:
    """
    Return bugs that match **all** supplied filter criteria.

    :param keyword:     Case-insensitive substring matched against title
                        and description.  Empty string = no keyword filter.
    :param status:      Exact status string to filter on, e.g. 'Open'.
                        Empty string = all statuses.
    :param severity:    Exact severity string, e.g. 'High'.
                        Empty string = all severities.
    :param assignee_id: Filter to bugs assigned to this user ID.
                        None = all assignees (including unassigned).
    :param sort_by:     Bug field to sort results by (default 'priority_score').
    :param ascending:   True = sort ascending; False = descending (default).
    :return:            Filtered, sorted list of bug dictionaries.
    """
    bugs = db.get_all_bugs()

    # 1. Keyword filter — searches title and description
    if keyword:
        kw = keyword.lower()
        bugs = [
            b for b in bugs
            if kw in b["title"].lower() or kw in b["description"].lower()
        ]

    # 2. Status filter
    if status:
        bugs = [b for b in bugs if b["status"] == status]

    # 3. Severity filter
    if severity:
        bugs = [b for b in bugs if b["severity"] == severity]

    # 4. Assignee filter
    if assignee_id is not None:
        bugs = [b for b in bugs if b.get("assigned_to") == assignee_id]

    # 5. Sort (use 0 as fallback so None values don't cause TypeError)
    bugs = sorted(
        bugs,
        key=lambda b: (b.get(sort_by) or 0),
        reverse=not ascending,
    )

    return bugs
