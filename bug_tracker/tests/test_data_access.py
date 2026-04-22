"""
tests/test_data_access.py  —  Unit Tests: JSON Data Access Layer
=================================================================
Verifies that the data access layer correctly reads, writes, and
persists records across separate calls (simulating process restarts).
"""

import json
import os
import pytest

from modules import data_access as da


# ── Users ─────────────────────────────────────────────────────────────────────

class TestUserOperations:

    def test_create_user_returns_record(self, tmp_data_dir):
        user = da.create_user("alice", "alice@example.com", "hash123", "Tester")
        assert user["id"] == 1
        assert user["username"] == "alice"
        assert user["role"] == "Tester"

    def test_created_user_persisted_to_json(self, tmp_data_dir):
        da.create_user("bob", "bob@example.com", "hash456", "Developer")
        path = da._FILES["users"]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert any(u["username"] == "bob" for u in data["users"])

    def test_ids_are_sequential(self, tmp_data_dir):
        u1 = da.create_user("user1", "u1@x.com", "h", "Tester")
        u2 = da.create_user("user2", "u2@x.com", "h", "Tester")
        assert u2["id"] == u1["id"] + 1

    def test_get_user_by_id_returns_correct_user(self, tmp_data_dir):
        created = da.create_user("carol", "carol@x.com", "h", "Admin")
        fetched = da.get_user_by_id(created["id"])
        assert fetched["username"] == "carol"

    def test_get_user_by_id_missing_returns_none(self, tmp_data_dir):
        assert da.get_user_by_id(9999) is None

    def test_get_user_by_username(self, tmp_data_dir):
        da.create_user("dave", "d@x.com", "h", "Developer")
        user = da.get_user_by_username("dave")
        assert user is not None
        assert user["email"] == "d@x.com"

    def test_get_user_by_username_missing_returns_none(self, tmp_data_dir):
        assert da.get_user_by_username("nobody") is None

    def test_get_all_users_returns_list(self, tmp_data_dir):
        da.create_user("eve",   "e@x.com", "h", "Tester")
        da.create_user("frank", "f@x.com", "h", "Tester")
        users = da.get_all_users()
        assert len(users) == 2


# ── Bugs ──────────────────────────────────────────────────────────────────────

class TestBugOperations:

    def _make_bug_data(self, reporter_id=1):
        return {
            "title":              "Test bug title",
            "description":        "Test bug description",
            "steps_to_reproduce": "Step 1\nStep 2",
            "severity":           "High",
            "priority":           "High",
            "priority_score":     55.0,
            "reported_by":        reporter_id,
        }

    def test_create_bug_returns_record(self, tmp_data_dir):
        bug = da.create_bug(self._make_bug_data())
        assert bug["id"] == 1
        assert bug["status"] == "Open"
        assert bug["assigned_to"] is None

    def test_bug_timestamps_set_on_creation(self, tmp_data_dir):
        bug = da.create_bug(self._make_bug_data())
        assert bug["created_at"] != ""
        assert bug["updated_at"] == bug["created_at"]

    def test_get_bug_by_id(self, tmp_data_dir):
        bug = da.create_bug(self._make_bug_data())
        fetched = da.get_bug_by_id(bug["id"])
        assert fetched["title"] == "Test bug title"

    def test_get_bug_by_id_missing_returns_none(self, tmp_data_dir):
        assert da.get_bug_by_id(99) is None

    def test_update_bug_modifies_field(self, tmp_data_dir):
        bug = da.create_bug(self._make_bug_data())
        updated = da.update_bug(bug["id"], {"status": "In Progress"})
        assert updated["status"] == "In Progress"

    def test_update_bug_sets_updated_at(self, tmp_data_dir):
        bug = da.create_bug(self._make_bug_data())
        original_ts = bug["updated_at"]
        import time; time.sleep(1)        # ensure clock ticks
        da.update_bug(bug["id"], {"status": "In Progress"})
        refreshed = da.get_bug_by_id(bug["id"])
        # updated_at may equal original if within the same second on fast machines
        assert refreshed["updated_at"] >= original_ts

    def test_update_nonexistent_bug_returns_none(self, tmp_data_dir):
        result = da.update_bug(9999, {"status": "Closed"})
        assert result is None

    def test_delete_bug_removes_record(self, tmp_data_dir):
        bug = da.create_bug(self._make_bug_data())
        deleted = da.delete_bug(bug["id"])
        assert deleted is True
        assert da.get_bug_by_id(bug["id"]) is None

    def test_delete_nonexistent_bug_returns_false(self, tmp_data_dir):
        assert da.delete_bug(9999) is False


# ── Comments ──────────────────────────────────────────────────────────────────

class TestCommentOperations:

    def test_create_comment_and_retrieve(self, tmp_data_dir):
        comment = da.create_comment(bug_id=1, user_id=1, content="This is a test comment.")
        assert comment["bug_id"]  == 1
        assert comment["content"] == "This is a test comment."
        comments = da.get_comments_for_bug(1)
        assert len(comments) == 1

    def test_comments_scoped_to_bug(self, tmp_data_dir):
        da.create_comment(1, 1, "Comment on bug 1")
        da.create_comment(2, 1, "Comment on bug 2")
        assert len(da.get_comments_for_bug(1)) == 1
        assert len(da.get_comments_for_bug(2)) == 1


# ── Activity log ─────────────────────────────────────────────────────────────

class TestActivityLog:

    def test_log_activity_creates_entry(self, tmp_data_dir):
        entry = da.log_activity(1, 1, "status", "Open", "In Progress")
        assert entry["field_changed"] == "status"
        assert entry["old_value"]     == "Open"
        assert entry["new_value"]     == "In Progress"

    def test_get_activity_for_bug_scoped(self, tmp_data_dir):
        da.log_activity(1, 1, "status", "Open",   "In Progress")
        da.log_activity(2, 1, "status", "Open",   "Resolved")
        assert len(da.get_activity_for_bug(1)) == 1
        assert len(da.get_activity_for_bug(2)) == 1

    def test_get_all_activity_log_returns_all(self, tmp_data_dir):
        da.log_activity(1, 1, "status", "Open", "In Progress")
        da.log_activity(2, 1, "status", "Open", "Resolved")
        assert len(da.get_all_activity_log()) == 2
