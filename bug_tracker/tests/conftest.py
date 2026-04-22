"""
tests/conftest.py  —  Pytest Fixtures
=======================================
Shared fixtures used across all test modules.

Key fixture: `tmp_data_dir`
    Redirects the data_access module to use a temporary directory instead
    of the real data/ folder.  This ensures every test starts with a clean
    slate and never touches production data.

Key fixture: `flask_client`
    Provides a Flask test client with the secret key set and the temp data
    directory wired in.
"""

import json
import os
import pytest

import app as flask_app
from modules import data_access as da


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    """
    Redirect all JSON file paths to a fresh temporary directory.

    `autouse=True` means this fixture runs for every test automatically,
    so no test can accidentally mutate the real data files.
    """
    tmp_data = tmp_path / "data"
    tmp_data.mkdir()

    new_files = {
        "users":        str(tmp_data / "users.json"),
        "bugs":         str(tmp_data / "bugs.json"),
        "comments":     str(tmp_data / "comments.json"),
        "activity_log": str(tmp_data / "activity_log.json"),
    }
    monkeypatch.setattr(da, "_FILES", new_files)
    return tmp_data


@pytest.fixture
def flask_client(tmp_data_dir):
    """Return a Flask test client backed by the temporary data directory."""
    flask_app.app.config["TESTING"]    = True
    flask_app.app.config["SECRET_KEY"] = "test-secret"
    with flask_app.app.test_client() as client:
        yield client


@pytest.fixture
def registered_user(tmp_data_dir):
    """Create and return a standard Tester user for use in tests."""
    from modules.auth import register_user
    user, _ = register_user("testuser", "test@example.com", "Password123", "Tester")
    return user


@pytest.fixture
def admin_user(tmp_data_dir):
    """Create and return an Admin user for use in tests."""
    from modules.auth import register_user
    user, _ = register_user("adminuser", "admin@example.com", "AdminPass1", "Admin")
    return user


@pytest.fixture
def sample_bug(registered_user):
    """Create and return a sample bug report for use in tests."""
    from modules.bug_manager import create_bug
    bug, _ = create_bug(
        title="Login button unresponsive",
        description="Clicking the login button does nothing on Chrome 120.",
        steps="1. Open login page\n2. Enter credentials\n3. Click Login",
        severity="High",
        reported_by=registered_user["id"],
        related_count=1,
    )
    return bug
