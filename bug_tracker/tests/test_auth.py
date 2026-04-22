"""
tests/test_auth.py  —  Unit Tests: Authentication Module
==========================================================
Covers:
  • Password hashing and verification
  • User registration (valid + BVA boundary cases)
  • Login (valid + invalid credentials)
  • Status-transition validation (all paths → V(G) = 4)

Technique: Boundary Value Analysis (BVA) on username (3–50 chars)
           and password (8–64 chars) field lengths.
"""

import pytest
from modules.auth import (
    hash_password,
    verify_password,
    register_user,
    login_user,
    is_valid_transition,
    VALID_TRANSITIONS,
)


# ── Password helpers ─────────────────────────────────────────────────────────

class TestPasswordHashing:

    def test_hash_returns_string(self):
        h = hash_password("mypassword")
        assert isinstance(h, str)

    def test_hash_starts_with_bcrypt_prefix(self):
        h = hash_password("mypassword")
        assert h.startswith("$2b$")

    def test_different_calls_produce_different_hashes(self):
        """bcrypt salt is random — two hashes of the same password must differ."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_verify_correct_password_returns_true(self):
        h = hash_password("correct_password")
        assert verify_password("correct_password", h) is True

    def test_verify_wrong_password_returns_false(self):
        h = hash_password("correct_password")
        assert verify_password("wrong_password", h) is False

    def test_verify_empty_password_returns_false(self):
        h = hash_password("correct_password")
        assert verify_password("", h) is False


# ── Registration — BVA on username length (boundary: 3–50 chars) ─────────────

class TestRegistrationUsernameBVA:
    """
    BVA test set for username length.
    Boundary values: 2 (invalid), 3 (valid), 25 (mid), 50 (valid), 51 (invalid).
    """

    def test_username_length_2_rejected(self):
        _, err = register_user("ab", "a@b.com", "Password1", "Tester")
        assert err is not None

    def test_username_length_3_accepted(self):
        user, err = register_user("abc", "abc@b.com", "Password1", "Tester")
        assert err is None
        assert user["username"] == "abc"

    def test_username_length_25_accepted(self):
        uname = "a" * 25
        user, err = register_user(uname, "mid@b.com", "Password1", "Tester")
        assert err is None

    def test_username_length_50_accepted(self):
        uname = "a" * 50
        user, err = register_user(uname, "max@b.com", "Password1", "Tester")
        assert err is None

    def test_username_length_51_rejected(self):
        uname = "a" * 51
        _, err = register_user(uname, "over@b.com", "Password1", "Tester")
        assert err is not None


# ── Registration — BVA on password length (boundary: 8–64 chars) ─────────────

class TestRegistrationPasswordBVA:

    def test_password_length_7_rejected(self):
        _, err = register_user("user7pw", "x@y.com", "Short7!", "Tester")
        assert err is not None

    def test_password_length_8_accepted(self):
        user, err = register_user("user8pw", "x@y.com", "Exactly8", "Tester")
        assert err is None

    def test_password_length_64_accepted(self):
        pw = "A" * 64
        user, err = register_user("user64pw", "x@y.com", pw, "Tester")
        assert err is None

    def test_password_length_65_rejected(self):
        pw = "A" * 65
        _, err = register_user("user65pw", "x@y.com", pw, "Tester")
        assert err is not None


# ── Registration — other validations ─────────────────────────────────────────

class TestRegistrationValidation:

    def test_invalid_email_rejected(self):
        _, err = register_user("gooduser", "notanemail", "Password1", "Tester")
        assert err is not None

    def test_email_with_space_rejected(self):
        _, err = register_user("gooduser2", "a @b.com", "Password1", "Tester")
        assert err is not None

    def test_invalid_role_rejected(self):
        _, err = register_user("gooduser3", "a@b.com", "Password1", "Hacker")
        assert err is not None

    def test_duplicate_username_rejected(self):
        register_user("dupuser", "a@b.com", "Password1", "Tester")
        _, err = register_user("dupuser", "b@c.com", "Password2", "Tester")
        assert err is not None

    def test_successful_registration_returns_user(self):
        user, err = register_user("newuser", "new@example.com", "SecurePass1", "Developer")
        assert err is None
        assert user["username"] == "newuser"
        assert user["role"] == "Developer"
        assert "password_hash" in user


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:

    def setup_method(self):
        register_user("logintest", "login@example.com", "MyPassword1", "Tester")

    def test_valid_credentials_return_user(self):
        user, err = login_user("logintest", "MyPassword1")
        assert err is None
        assert user["username"] == "logintest"

    def test_wrong_password_returns_error(self):
        _, err = login_user("logintest", "WrongPass")
        assert err is not None

    def test_unknown_username_returns_error(self):
        _, err = login_user("nobody", "MyPassword1")
        assert err is not None

    def test_empty_username_returns_error(self):
        _, err = login_user("", "MyPassword1")
        assert err is not None

    def test_empty_password_returns_error(self):
        _, err = login_user("logintest", "")
        assert err is not None

    def test_error_message_is_vague(self):
        """Both bad username and bad password must return the same message
        to prevent username enumeration attacks."""
        _, err_bad_user = login_user("nobody",    "MyPassword1")
        _, err_bad_pass = login_user("logintest", "BadPassword")
        assert err_bad_user == err_bad_pass


# ── Status-transition validation (basis-path coverage, V(G) = 4) ─────────────

class TestStatusTransition:
    """
    Tests every edge in the status transition graph.
    V(G) = 4 independent paths are exercised below.
    """

    # Valid transitions
    def test_open_to_in_progress(self):
        assert is_valid_transition("Open", "In Progress") is True

    def test_in_progress_to_resolved(self):
        assert is_valid_transition("In Progress", "Resolved") is True

    def test_in_progress_to_open(self):
        assert is_valid_transition("In Progress", "Open") is True

    def test_resolved_to_closed(self):
        assert is_valid_transition("Resolved", "Closed") is True

    def test_resolved_to_in_progress(self):
        assert is_valid_transition("Resolved", "In Progress") is True

    # Invalid transitions (skip / reverse)
    def test_open_to_closed_is_invalid(self):
        assert is_valid_transition("Open", "Closed") is False

    def test_open_to_resolved_is_invalid(self):
        assert is_valid_transition("Open", "Resolved") is False

    def test_closed_has_no_valid_transitions(self):
        for status in ("Open", "In Progress", "Resolved", "Closed"):
            assert is_valid_transition("Closed", status) is False

    def test_unknown_current_status_returns_false(self):
        assert is_valid_transition("Pending", "Open") is False
