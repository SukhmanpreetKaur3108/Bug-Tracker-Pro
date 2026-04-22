"""
tests/test_selenium.py  —  UI Automation Tests (Selenium WebDriver)
====================================================================
End-to-end tests that drive a real browser to verify the full
user-facing workflow.

Prerequisites
-------------
1.  The Flask application must be running:
        python app.py

2.  ChromeDriver must be installed and on your PATH:
        https://chromedriver.chromium.org/downloads
    (version must match your installed Chrome browser)

3.  Install Selenium:
        pip install selenium

Run
---
    pytest tests/test_selenium.py -v

These tests are intentionally skipped when the live server is not
reachable, so they never block the unit-test suite.
"""

import time
import pytest

# ── Skip the entire module if Selenium is not installed ───────────────────────
selenium = pytest.importorskip("selenium", reason="selenium not installed")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL    = "http://127.0.0.1:5000"
WAIT_SECS   = 6     # implicit wait timeout
TEST_USER   = "selenium_user"
TEST_PASS   = "SeleniumPass1"
TEST_EMAIL  = "selenium@test.com"


# ── Helper: check server is live ──────────────────────────────────────────────

def _server_is_live() -> bool:
    """Return True if the Flask dev server is accepting connections."""
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", 5000), timeout=2)
        s.close()
        return True
    except OSError:
        return False


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def driver():
    """
    Create a headless Chrome WebDriver for the test session.
    Skips the entire module if the dev server is not running.
    """
    if not _server_is_live():
        pytest.skip("Flask dev server not running — skipping Selenium tests.")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")      # run without opening a window
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    try:
        drv = webdriver.Chrome(options=options)
    except WebDriverException as exc:
        pytest.skip(f"ChromeDriver not found: {exc}")

    drv.implicitly_wait(WAIT_SECS)
    yield drv
    drv.quit()


@pytest.fixture(scope="module")
def wait(driver):
    return WebDriverWait(driver, WAIT_SECS)


# ── Page Object helpers ───────────────────────────────────────────────────────

def go(driver, path: str):
    """Navigate to a URL path on the local server."""
    driver.get(f"{BASE_URL}{path}")


def find(driver, by, value):
    return driver.find_element(by, value)


def fill(driver, name: str, value: str):
    el = driver.find_element(By.NAME, name)
    el.clear()
    el.send_keys(value)


def click(driver, by, value):
    driver.find_element(by, value).click()


def assert_flash(driver, text: str):
    """Assert that a flash message containing *text* is visible."""
    body = driver.find_element(By.TAG_NAME, "body").text
    assert text.lower() in body.lower(), (
        f"Expected flash message containing '{text}'. Page text:\n{body[:500]}"
    )


# ── Test 1: Registration ──────────────────────────────────────────────────────

class TestRegistration:

    def test_register_new_user(self, driver, wait):
        """Valid registration should redirect to login with a success flash."""
        go(driver, "/register")
        fill(driver, "username", TEST_USER)
        fill(driver, "email",    TEST_EMAIL)
        fill(driver, "password", TEST_PASS)
        Select(driver.find_element(By.NAME, "role")).select_by_value("Tester")
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        wait.until(EC.url_contains("/login"))
        assert_flash(driver, "Account created")

    def test_register_duplicate_username_shows_error(self, driver):
        """Registering the same username twice must show an error."""
        go(driver, "/register")
        fill(driver, "username", TEST_USER)          # same username
        fill(driver, "email",    "other@test.com")
        fill(driver, "password", TEST_PASS)
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        assert_flash(driver, "already taken")

    def test_register_short_username_shows_error(self, driver):
        """Username < 3 chars should be rejected."""
        go(driver, "/register")
        fill(driver, "username", "ab")
        fill(driver, "email",    "ab@test.com")
        fill(driver, "password", TEST_PASS)
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        # HTML5 minlength prevents submission, so we stay on /register
        assert "/register" in driver.current_url or "3 and 50" in driver.page_source


# ── Test 2: Login ─────────────────────────────────────────────────────────────

class TestLogin:

    def test_login_invalid_credentials_shows_error(self, driver):
        go(driver, "/login")
        fill(driver, "username", TEST_USER)
        fill(driver, "password", "WrongPassword")
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        assert_flash(driver, "Invalid username or password")

    def test_login_empty_fields_stay_on_page(self, driver):
        go(driver, "/login")
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        assert "/login" in driver.current_url

    def test_login_valid_redirects_to_dashboard(self, driver, wait):
        go(driver, "/login")
        fill(driver, "username", TEST_USER)
        fill(driver, "password", TEST_PASS)
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        wait.until(EC.url_contains("/dashboard"))
        assert "Dashboard" in driver.page_source


# ── Test 3: Bug creation ──────────────────────────────────────────────────────

class TestBugCreation:

    def test_create_bug_appears_in_list(self, driver, wait):
        go(driver, "/bugs/new")
        fill(driver, "title",       "Selenium Test Bug — Login Crash")
        fill(driver, "description", "Clicking login with empty fields crashes the server.")
        fill(driver, "steps",       "1. Open login page\n2. Click submit\n3. Observe 500 error")
        Select(driver.find_element(By.NAME, "severity")).select_by_value("High")
        fill(driver, "related_count", "2")
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        # Should redirect to the bug detail page
        wait.until(EC.url_contains("/bugs/"))
        assert "Selenium Test Bug" in driver.page_source

    def test_create_bug_empty_title_stays_on_form(self, driver):
        """HTML5 required attribute keeps the form open on empty title."""
        go(driver, "/bugs/new")
        # Leave title empty, fill description
        fill(driver, "description", "Valid description here.")
        click(driver, By.CSS_SELECTOR, "button[type='submit']")
        assert "/bugs/new" in driver.current_url


# ── Test 4: Bug detail & status change ───────────────────────────────────────

class TestBugDetail:

    @pytest.fixture(autouse=True, scope="class")
    def navigate_to_first_bug(self, driver, wait):
        """Navigate to the bug list and open the first bug."""
        go(driver, "/bugs")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".data-table a")))
        driver.find_elements(By.CSS_SELECTOR, ".data-table tbody a")[0].click()
        wait.until(EC.url_matches(r".*/bugs/\d+$"))

    def test_bug_detail_shows_description(self, driver):
        assert "Selenium Test Bug" in driver.page_source

    def test_status_change_to_in_progress(self, driver, wait):
        """Select 'In Progress' from the status dropdown and submit."""
        select_el = driver.find_element(By.NAME, "status")
        Select(select_el).select_by_value("In Progress")
        select_el.find_element(By.XPATH, "..").find_element(
            By.CSS_SELECTOR, "button[type='submit']"
        ).click()
        wait.until(EC.url_matches(r".*/bugs/\d+$"))
        assert_flash(driver, "In Progress")


# ── Test 5: Comment ───────────────────────────────────────────────────────────

class TestComment:

    def test_add_comment_appears_on_page(self, driver, wait):
        go(driver, "/bugs")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".data-table a")))
        driver.find_elements(By.CSS_SELECTOR, ".data-table tbody a")[0].click()
        wait.until(EC.presence_of_element_located((By.NAME, "content")))

        fill(driver, "content", "I can reproduce this on Firefox too.")
        click(driver, By.CSS_SELECTOR, ".comment-form button[type='submit']")
        wait.until(EC.url_matches(r".*/bugs/\d+$"))
        assert "I can reproduce this on Firefox too." in driver.page_source


# ── Test 6: Search ────────────────────────────────────────────────────────────

class TestSearch:

    def test_keyword_search_returns_matching_bug(self, driver, wait):
        go(driver, "/bugs?q=Selenium+Test+Bug")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".data-table")))
        assert "Selenium Test Bug" in driver.page_source

    def test_keyword_search_no_match_shows_empty_message(self, driver, wait):
        go(driver, "/bugs?q=xxxxnomatchxxxx")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert "No bugs match" in driver.page_source


# ── Test 7: Logout ────────────────────────────────────────────────────────────

class TestLogout:

    def test_logout_redirects_to_login(self, driver, wait):
        go(driver, "/logout")
        wait.until(EC.url_contains("/login"))
        assert_flash(driver, "logged out")

    def test_protected_page_redirects_after_logout(self, driver, wait):
        """Accessing /dashboard after logout should redirect to /login."""
        go(driver, "/dashboard")
        wait.until(EC.url_contains("/login"))
