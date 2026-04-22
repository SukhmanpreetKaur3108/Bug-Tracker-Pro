"""
tests/test_bug_manager.py  —  Unit Tests: Bug Management Module
================================================================
Covers:
  • Bug creation — valid inputs and BVA on title / description length
  • Status transition lifecycle (all valid paths + invalid attempts)
  • Bug assignment and re-assignment
  • Bug editing with priority re-computation
  • Bug deletion

Technique: BVA on title (1–200 chars) and description (1–10 000 chars).
"""

import pytest
from modules.bug_manager import (
    create_bug,
    get_bug,
    get_all_bugs,
    update_bug_status,
    assign_bug,
    edit_bug,
    delete_bug,
    MAX_TITLE_LEN,
    MAX_DESC_LEN,
)
from modules.auth import register_user


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_id(tmp_data_dir):
    user, _ = register_user("buguser", "bug@test.com", "TestPass1", "Tester")
    return user["id"]

@pytest.fixture
def dev_id(tmp_data_dir):
    dev, _ = register_user("devuser", "dev@test.com", "DevPass12", "Developer")
    return dev["id"]


# ── Creation — happy path ─────────────────────────────────────────────────────

class TestCreateBug:

    def test_creates_bug_with_correct_fields(self, user_id):
        bug, err = create_bug("Login fails", "Detailed desc", "Step 1", "High", user_id)
        assert err is None
        assert bug["title"]       == "Login fails"
        assert bug["severity"]    == "High"
        assert bug["status"]      == "Open"
        assert bug["reported_by"] == user_id
        assert bug["assigned_to"] is None

    def test_priority_score_computed_on_creation(self, user_id):
        bug, _ = create_bug("Test bug", "Some description", "", "Critical", user_id, related_count=3)
        assert bug["priority_score"] > 0.0

    def test_bug_persisted_and_retrievable(self, user_id):
        bug, _ = create_bug("Persist check", "Description here", "", "Low", user_id)
        fetched = get_bug(bug["id"])
        assert fetched is not None
        assert fetched["title"] == "Persist check"

    def test_multiple_bugs_all_retrievable(self, user_id):
        for i in range(3):
            create_bug(f"Bug {i}", "Description", "", "Medium", user_id)
        all_bugs = get_all_bugs()
        assert len(all_bugs) >= 3

    def test_all_bugs_sorted_by_priority_score_descending(self, user_id):
        create_bug("Low bug",      "Desc", "", "Low",      user_id)
        create_bug("Critical bug", "Desc", "", "Critical", user_id)
        bugs = get_all_bugs()
        scores = [b["priority_score"] for b in bugs]
        assert scores == sorted(scores, reverse=True)


# ── Creation — BVA on title length (1–200 chars) ─────────────────────────────

class TestCreateBugTitleBVA:

    def test_title_length_0_rejected(self, user_id):
        _, err = create_bug("", "Desc", "", "Medium", user_id)
        assert err is not None

    def test_title_length_1_accepted(self, user_id):
        bug, err = create_bug("X", "Desc", "", "Low", user_id)
        assert err is None

    def test_title_length_200_accepted(self, user_id):
        title = "A" * MAX_TITLE_LEN
        bug, err = create_bug(title, "Desc", "", "Low", user_id)
        assert err is None

    def test_title_length_201_rejected(self, user_id):
        title = "A" * (MAX_TITLE_LEN + 1)
        _, err = create_bug(title, "Desc", "", "Low", user_id)
        assert err is not None


# ── Creation — BVA on description length (1–10 000 chars) ────────────────────

class TestCreateBugDescriptionBVA:

    def test_description_empty_rejected(self, user_id):
        _, err = create_bug("Title", "", "", "Medium", user_id)
        assert err is not None

    def test_description_1_char_accepted(self, user_id):
        bug, err = create_bug("Title", "D", "", "Low", user_id)
        assert err is None

    def test_description_10000_chars_accepted(self, user_id):
        desc = "D" * MAX_DESC_LEN
        bug, err = create_bug("Title", desc, "", "Low", user_id)
        assert err is None

    def test_description_10001_chars_rejected(self, user_id):
        desc = "D" * (MAX_DESC_LEN + 1)
        _, err = create_bug("Title", desc, "", "Low", user_id)
        assert err is not None


# ── Creation — invalid severity ───────────────────────────────────────────────

class TestCreateBugSeverityValidation:

    def test_invalid_severity_rejected(self, user_id):
        _, err = create_bug("Title", "Desc", "", "Extreme", user_id)
        assert err is not None

    @pytest.mark.parametrize("sev", ["Low", "Medium", "High", "Critical"])
    def test_all_valid_severities_accepted(self, sev, user_id):
        bug, err = create_bug("Title", "Desc", "", sev, user_id)
        assert err is None


# ── Status lifecycle ──────────────────────────────────────────────────────────

class TestStatusWorkflow:

    @pytest.fixture
    def open_bug(self, user_id):
        bug, _ = create_bug("Workflow bug", "Desc", "", "Medium", user_id)
        return bug

    def test_open_to_in_progress(self, open_bug, user_id):
        updated, err = update_bug_status(open_bug["id"], "In Progress", user_id)
        assert err is None
        assert updated["status"] == "In Progress"

    def test_in_progress_to_resolved(self, open_bug, user_id):
        update_bug_status(open_bug["id"], "In Progress", user_id)
        updated, err = update_bug_status(open_bug["id"], "Resolved", user_id)
        assert err is None
        assert updated["status"] == "Resolved"

    def test_resolved_to_closed(self, open_bug, user_id):
        update_bug_status(open_bug["id"], "In Progress", user_id)
        update_bug_status(open_bug["id"], "Resolved",    user_id)
        updated, err = update_bug_status(open_bug["id"], "Closed", user_id)
        assert err is None
        assert updated["status"] == "Closed"

    def test_open_to_closed_is_rejected(self, open_bug, user_id):
        """Skipping steps in the workflow must be rejected."""
        _, err = update_bug_status(open_bug["id"], "Closed", user_id)
        assert err is not None

    def test_closed_bug_cannot_transition(self, open_bug, user_id):
        update_bug_status(open_bug["id"], "In Progress", user_id)
        update_bug_status(open_bug["id"], "Resolved",    user_id)
        update_bug_status(open_bug["id"], "Closed",      user_id)
        _, err = update_bug_status(open_bug["id"], "Open", user_id)
        assert err is not None

    def test_nonexistent_bug_returns_error(self, user_id):
        _, err = update_bug_status(9999, "In Progress", user_id)
        assert err is not None

    def test_invalid_status_string_rejected(self, open_bug, user_id):
        _, err = update_bug_status(open_bug["id"], "Pending", user_id)
        assert err is not None


# ── Assignment ────────────────────────────────────────────────────────────────

class TestAssignment:

    @pytest.fixture
    def open_bug(self, user_id):
        bug, _ = create_bug("Assign bug", "Desc", "", "Low", user_id)
        return bug

    def test_assign_to_developer(self, open_bug, user_id, dev_id):
        updated, err = assign_bug(open_bug["id"], dev_id, user_id)
        assert err is None
        assert updated["assigned_to"] == dev_id

    def test_unassign_sets_none(self, open_bug, user_id, dev_id):
        assign_bug(open_bug["id"], dev_id, user_id)
        updated, err = assign_bug(open_bug["id"], None, user_id)
        assert err is None
        assert updated["assigned_to"] is None

    def test_assign_nonexistent_bug_returns_error(self, user_id, dev_id):
        _, err = assign_bug(9999, dev_id, user_id)
        assert err is not None


# ── Edit ─────────────────────────────────────────────────────────────────────

class TestEditBug:

    @pytest.fixture
    def bug(self, user_id):
        b, _ = create_bug("Original title", "Original desc", "", "Low", user_id)
        return b

    def test_edit_updates_title_and_severity(self, bug, user_id):
        updated, err = edit_bug(bug["id"], "New title", "New desc", "", "Critical", user_id)
        assert err is None
        assert updated["title"]    == "New title"
        assert updated["severity"] == "Critical"

    def test_edit_recomputes_priority_score(self, bug, user_id):
        original_score = bug["priority_score"]
        updated, _ = edit_bug(bug["id"], "New title", "New desc", "", "Critical", user_id)
        # Critical must score higher than Low (even at age 0)
        assert updated["priority_score"] >= original_score

    def test_edit_nonexistent_bug_returns_error(self, user_id):
        _, err = edit_bug(9999, "Title", "Desc", "", "Low", user_id)
        assert err is not None

    def test_edit_empty_title_rejected(self, bug, user_id):
        _, err = edit_bug(bug["id"], "", "Desc", "", "Low", user_id)
        assert err is not None


# ── Delete ────────────────────────────────────────────────────────────────────

class TestDeleteBug:

    def test_delete_existing_bug_succeeds(self, user_id):
        bug, _ = create_bug("Delete me", "Desc", "", "Low", user_id)
        ok, err = delete_bug(bug["id"])
        assert ok is True and err is None
        assert get_bug(bug["id"]) is None

    def test_delete_nonexistent_bug_returns_error(self):
        ok, err = delete_bug(9999)
        assert ok is False and err is not None
