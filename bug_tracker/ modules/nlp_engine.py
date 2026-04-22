"""
modules/nlp_engine.py  —  NLP Engine
======================================
Provides three intelligent features:
  1. Duplicate bug detection  — TF-IDF cosine similarity
  2. Severity auto-suggestion — keyword scoring
  3. Module-wise clustering   — keyword-based module grouping

No external API needed — uses scikit-learn only.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# 1. Duplicate Bug Detection
# ---------------------------------------------------------------------------

DUPLICATE_THRESHOLD = 0.55   # cosine similarity above this → likely duplicate

def find_duplicates(new_title: str, new_desc: str, existing_bugs: list) -> list:
    """
    Compare a new bug against all existing bugs using TF-IDF cosine similarity.

    :param new_title:      Title of the new bug being reported.
    :param new_desc:       Description of the new bug.
    :param existing_bugs:  List of existing bug dicts from the data store.
    :return:               List of (bug_dict, similarity_score) tuples where
                           score >= DUPLICATE_THRESHOLD, sorted by score desc.
    """
    if not existing_bugs:
        return []

    new_text = f"{new_title} {new_desc}".lower().strip()
    existing_texts = [
        f"{b['title']} {b['description']}".lower().strip()
        for b in existing_bugs
    ]

    # Need at least 2 documents for TF-IDF to work meaningfully
    all_texts = [new_text] + existing_texts
    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    except ValueError:
        return []

    results = []
    for bug, score in zip(existing_bugs, similarities):
        if score >= DUPLICATE_THRESHOLD:
            results.append((bug, round(float(score), 3)))

    return sorted(results, key=lambda x: x[1], reverse=True)[:5]


# ---------------------------------------------------------------------------
# 2. Severity Auto-Suggestion
# ---------------------------------------------------------------------------

_SEVERITY_KEYWORDS = {
    "Critical": [
        "crash", "crashes", "crashing", "down", "outage", "unavailable",
        "data loss", "corruption", "broken", "failure", "fatal", "exception",
        "not working", "completely", "server error", "500", "404",
    ],
    "High": [
        "slow", "lag", "lagging", "wrong", "incorrect", "missing", "cannot",
        "can't", "unable", "failed", "fails", "blocked", "security",
        "vulnerability", "timeout", "hang", "freeze",
    ],
    "Medium": [
        "sometimes", "occasionally", "intermittent", "partial", "minor issue",
        "not always", "unexpected", "weird", "strange", "confusing",
    ],
    "Low": [
        "cosmetic", "typo", "color", "colour", "font", "alignment",
        "spacing", "layout", "ui", "display", "style", "tooltip",
        "wording", "grammar",
    ],
}

def suggest_severity(title: str, description: str) -> tuple[str, dict]:
    """
    Suggest a severity level based on keyword scoring.

    :param title:       Bug title.
    :param description: Bug description.
    :return:            (suggested_severity, scores_dict) — scores show why.
    """
    text = f"{title} {description}".lower()
    scores = {sev: 0 for sev in _SEVERITY_KEYWORDS}

    for severity, keywords in _SEVERITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[severity] += 1

    # Default to Medium if nothing matches
    best = max(scores, key=lambda s: scores[s])
    if scores[best] == 0:
        best = "Medium"

    return best, scores


# ---------------------------------------------------------------------------
# 3. Module-wise Bug Clustering
# ---------------------------------------------------------------------------

_MODULE_KEYWORDS = {
    "Authentication": ["login", "logout", "password", "register", "session", "token", "auth", "credential"],
    "Dashboard":      ["dashboard", "chart", "graph", "stats", "analytics", "summary", "count"],
    "Bug Reporting":  ["bug", "report", "submit", "form", "ticket", "create", "new bug"],
    "Search/Filter":  ["search", "filter", "sort", "find", "query", "keyword"],
    "Assignment":     ["assign", "developer", "owner", "responsible", "allocated"],
    "Comments":       ["comment", "thread", "reply", "discussion", "message"],
    "UI/Frontend":    ["ui", "button", "page", "screen", "display", "layout", "style", "css"],
    "Performance":    ["slow", "lag", "speed", "performance", "timeout", "load"],
    "Data/Storage":   ["json", "data", "save", "file", "storage", "database", "export"],
    "General":        [],   # catch-all
}

def cluster_bugs_by_module(bugs: list) -> dict:
    """
    Group bugs into software modules based on keyword matching.

    :param bugs: List of bug dicts.
    :return:     Dict of {module_name: [bug_list]}.
    """
    clusters = {mod: [] for mod in _MODULE_KEYWORDS}

    for bug in bugs:
        text = f"{bug['title']} {bug['description']}".lower()
        matched = False
        for module, keywords in _MODULE_KEYWORDS.items():
            if module == "General":
                continue
            if any(kw in text for kw in keywords):
                clusters[module].append(bug)
                matched = True
                break
        if not matched:
            clusters["General"].append(bug)

    # Remove empty modules
    return {k: v for k, v in clusters.items() if v}
