"""
modules/ai_summarizer.py  —  AI Bug Summarizer
================================================
Converts a messy user description into a structured bug ticket
using the Groq API (free tier — llama3-8b-8192 model).

Setup:
  1. Get a free API key at https://console.groq.com
  2. Set the environment variable:
       Windows PowerShell: $env:GROQ_API_KEY = "your_key_here"
       Or add to a .env file and load with python-dotenv

If no API key is set, falls back to a rule-based summarizer
so the app still works without any API key.
"""

import os
import re

# ---------------------------------------------------------------------------
# Groq client (optional — graceful fallback if not installed / no key)
# ---------------------------------------------------------------------------
_groq_client = None
try:
    from groq import Groq
    _api_key = os.environ.get("GROQ_API_KEY", "")
    if _api_key:
        _groq_client = Groq(api_key=_api_key)
except ImportError:
    pass   # groq package not installed — use fallback

_SYSTEM_PROMPT = """You are an expert software QA engineer.
The user will give you a messy, informal bug description.
Your job is to extract and return ONLY this structured format (no extra text):

Title: <short one-line summary, max 10 words>
Module: <which part of the app is affected, e.g. Authentication, Dashboard, Search>
Severity: <one of: Low | Medium | High | Critical>
Crash Type: <e.g. UI glitch | Runtime error | Logic error | Performance issue | N/A>
Steps: <numbered steps to reproduce, or "Not specified">
Expected: <what should happen>
Actual: <what actually happens>
"""


def summarize_bug(raw_description: str) -> dict:
    """
    Convert a raw informal bug description into a structured dict.

    Uses Groq (llama3) when available; falls back to rule-based parsing.

    :param raw_description: Free-text bug report from the user.
    :return: Dict with keys: title, module, severity, crash_type, steps,
             expected, actual, used_ai (bool).
    """
    if _groq_client:
        return _groq_summarize(raw_description)
    return _rule_based_summarize(raw_description)


def ai_available() -> bool:
    """Return True if the Groq API client is configured and ready."""
    return _groq_client is not None


# ---------------------------------------------------------------------------
# Groq implementation
# ---------------------------------------------------------------------------

def _groq_summarize(text: str) -> dict:
    try:
        response = _groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": text},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw = response.choices[0].message.content
        return _parse_structured(raw, used_ai=True)
    except Exception as e:
        return _rule_based_summarize(text, error=str(e))


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

_CRASH_KEYWORDS = {
    "Runtime error":    ["crash", "exception", "error", "traceback", "500"],
    "UI glitch":        ["ui", "button", "layout", "display", "screen", "visual"],
    "Performance issue":["slow", "lag", "timeout", "freeze", "hang", "load"],
    "Logic error":      ["wrong", "incorrect", "unexpected", "invalid", "bad"],
}

def _rule_based_summarize(text: str, error: str = "") -> dict:
    text_lower = text.lower()

    # Detect crash type
    crash_type = "N/A"
    for ct, kws in _CRASH_KEYWORDS.items():
        if any(k in text_lower for k in kws):
            crash_type = ct
            break

    # Detect severity
    from modules.nlp_engine import suggest_severity
    severity, _ = suggest_severity("", text)

    # Generate a rough title (first sentence, max 10 words)
    first_sentence = re.split(r'[.!?\n]', text.strip())[0]
    words = first_sentence.split()
    title = " ".join(words[:10]).capitalize()
    if not title:
        title = "Bug reported by user"

    result = {
        "title":      title,
        "module":     "General",
        "severity":   severity,
        "crash_type": crash_type,
        "steps":      "Not specified — user did not provide steps.",
        "expected":   "Normal application behaviour.",
        "actual":     text.strip(),
        "used_ai":    False,
    }
    if error:
        result["ai_error"] = error
    return result


# ---------------------------------------------------------------------------
# Parser for Groq output
# ---------------------------------------------------------------------------

def _parse_structured(raw: str, used_ai: bool) -> dict:
    """Parse the structured text returned by the Groq model."""
    def extract(label):
        match = re.search(rf"{label}:\s*(.+)", raw, re.IGNORECASE)
        return match.group(1).strip() if match else "Not specified"

    return {
        "title":      extract("Title"),
        "module":     extract("Module"),
        "severity":   extract("Severity"),
        "crash_type": extract("Crash Type"),
        "steps":      extract("Steps"),
        "expected":   extract("Expected"),
        "actual":     extract("Actual"),
        "used_ai":    used_ai,
    }
