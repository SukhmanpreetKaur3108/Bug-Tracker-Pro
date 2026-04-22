"""
modules/comments.py  —  Comment Module
========================================
Manages comments on individual bug reports.
Comments are ordered oldest-first for chronological reading.
"""

from modules import data_access as db

MAX_COMMENT_LEN = 5_000   # characters


def add_comment(
    bug_id: int,
    user_id: int,
    content: str,
) -> tuple[dict | None, str | None]:
    """
    Add a comment to a bug report after validating inputs.

    :param bug_id:   ID of the bug being commented on.
    :param user_id:  ID of the user posting the comment.
    :param content:  Comment body text (1 – 5 000 characters).
    :return:         (comment_dict, None) on success; (None, error_message) on failure.
    """
    content = content.strip()

    if not content:
        return None, "Comment cannot be empty."
    if len(content) > MAX_COMMENT_LEN:
        return None, f"Comment must not exceed {MAX_COMMENT_LEN} characters."
    if db.get_bug_by_id(bug_id) is None:
        return None, "Bug not found."

    comment = db.create_comment(bug_id, user_id, content)
    return comment, None


def get_comments(bug_id: int) -> list:
    """
    Retrieve all comments for a bug, ordered oldest-first.

    :param bug_id: ID of the bug.
    :return:       List of comment dictionaries sorted by created_at ascending.
    """
    return sorted(
        db.get_comments_for_bug(bug_id),
        key=lambda c: c["created_at"],
    )
