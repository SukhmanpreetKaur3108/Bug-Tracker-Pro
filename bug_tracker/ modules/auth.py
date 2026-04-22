"""
modules/auth.py  —  Authentication Module
==========================================
Handles user registration, login verification, and the bug-status transition
rules (which encode business logic rather than data persistence).

Security design
---------------
* Passwords are hashed with bcrypt at cost-factor 12 — never stored in plain text.
* Login failure returns the same vague message regardless of whether the
  username exists, to prevent username enumeration.
* Input validation rejects out-of-range lengths before any hashing or I/O.

Status-transition graph
-----------------------
    Open  →  In Progress
    In Progress  →  Resolved  |  Open        (reopen if mis-diagnosed)
    Resolved     →  Closed    |  In Progress  (reopen if fix fails)
    Closed       →  (terminal — no further transitions)

Cyclomatic complexity of is_valid_transition: V(G) = 2  (one dict lookup + membership test).
"""

import bcrypt
from modules import data_access as db

# Allowlist of valid roles
VALID_ROLES = {"Admin", "Developer", "Tester"}

# Defines which transitions are permitted from each status
VALID_TRANSITIONS: dict[str, set[str]] = {
    "Open":        {"In Progress"},
    "In Progress": {"Resolved", "Open"},
    "Resolved":    {"Closed", "In Progress"},
    "Closed":      set(),
}


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plaintext: str) -> str:
    """
    Hash a plaintext password with bcrypt (cost factor 12).

    :param plaintext: The raw password string supplied by the user.
    :return:          A UTF-8 bcrypt hash string safe to store in JSON.
    """
    hashed = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    :param plaintext:    Raw password entered at login.
    :param stored_hash:  The previously hashed value from storage.
    :return:             True if the password matches; False otherwise.
    """
    return bcrypt.checkpw(plaintext.encode("utf-8"), stored_hash.encode("utf-8"))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(
    username: str,
    email: str,
    password: str,
    role: str,
) -> tuple[dict | None, str | None]:
    """
    Validate inputs, hash the password, and create a new user account.

    Validation rules (mirrors BVA boundaries from the test plan):
        username  : 3 – 50 characters, must be unique.
        password  : 8 – 64 characters.
        email     : must contain '@' and no spaces.
        role      : must be one of Admin / Developer / Tester.

    :param username: Desired username.
    :param email:    User's email address.
    :param password: Plaintext password (will be hashed before storage).
    :param role:     Account role.
    :return:         (user_dict, None) on success; (None, error_message) on failure.
    """
    username = username.strip()
    email    = email.strip()
    role     = role.strip()

    if not (3 <= len(username) <= 50):
        return None, "Username must be between 3 and 50 characters."
    if not (8 <= len(password) <= 64):
        return None, "Password must be between 8 and 64 characters."
    if "@" not in email or " " in email or len(email) < 5:
        return None, "Please enter a valid email address."
    if role not in VALID_ROLES:
        return None, f"Role must be one of: {', '.join(sorted(VALID_ROLES))}."
    if db.get_user_by_username(username) is not None:
        return None, f"Username '{username}' is already taken."

    password_hash = hash_password(password)
    user = db.create_user(username, email, password_hash, role)
    return user, None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login_user(username: str, password: str) -> tuple[dict | None, str | None]:
    """
    Authenticate a user by username and password.

    :param username: The username to look up (stripped of leading/trailing whitespace).
    :param password: The plaintext password to verify.
    :return:         (user_dict, None) on success; (None, error_message) on failure.
    """
    if not username or not password:
        return None, "Username and password are required."

    user = db.get_user_by_username(username.strip())

    # Deliberately vague: do not reveal whether the username exists
    if user is None or not verify_password(password, user["password_hash"]):
        return None, "Invalid username or password."

    return user, None


# ---------------------------------------------------------------------------
# Status-transition validation
# ---------------------------------------------------------------------------

def is_valid_transition(current_status: str, new_status: str) -> bool:
    """
    Return True only when transitioning from *current_status* to *new_status*
    is permitted by the bug lifecycle rules.

    :param current_status: The bug's current status string.
    :param new_status:     The desired next status string.
    :return:               True if the transition is allowed.
    """
    return new_status in VALID_TRANSITIONS.get(current_status, set())
