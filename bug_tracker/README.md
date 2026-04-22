# 🐛 Bug Tracker Pro

> **An AI-Enhanced Intelligent Bug Tracking and Defect Management System**  
> Course: CSL3050 — Software Engineering and Testing | B.Tech CS, Semester VI

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [Running the App](#running-the-app)
7. [Running Tests](#running-tests)
8. [Environment Variables](#environment-variables)
9. [User Roles](#user-roles)
10. [Bug Lifecycle](#bug-lifecycle)
11. [Priority Scoring](#priority-scoring)
12. [Screenshots](#screenshots)
13. [Acknowledgements](#acknowledgements)

---

## Overview

**Bug Tracker Pro** is a full-featured defect management system built as an academic project for the Software Engineering & Testing course. It combines a Streamlit-based web UI, a C-powered priority engine, NLP-based duplicate detection, an optional AI summarizer (Groq / LLaMA 3), interactive analytics dashboards, and a comprehensive test suite.

Inspired by industry-leading tools: **Jira**, **Bugzilla**, **GitHub Issues**, **Redmine**, and **YouTrack**.

---

## Features

| Feature | Details |
|---|---|
| 🔐 Authentication | Register / Login with bcrypt password hashing (cost-12) |
| 🐛 Bug Reporting | Title, description, severity, steps to reproduce, screenshot upload |
| 🤖 AI Summarizer | Groq LLaMA-3 structured bug summary (rule-based fallback if no key) |
| 🧠 NLP Duplicates | TF-IDF + cosine similarity detects similar bugs before submission |
| ⚡ Priority Engine | C shared library computes a 0–100 priority score via ctypes |
| 📊 Analytics | 5 interactive Plotly charts: donut, bar, scatter, Gantt timeline, trend |
| 📦 Export | Download bug list as CSV or PDF |
| 🗂️ Module Clustering | Keyword-based grouping of bugs into software modules |
| 🧪 Testing Panel | Embedded UAT table, defect log, editable test cases |
| 📝 Activity Log | Full audit trail of every status/field change |
| 💬 Comments | Per-bug threaded comments with timestamps |

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI Framework | Streamlit |
| Web API (legacy) | Flask 3.0 |
| Priority Engine | C (compiled via GCC) + Python ctypes |
| NLP | scikit-learn (TF-IDF, cosine similarity) |
| AI Summarizer | Groq API — LLaMA 3-8B (optional) |
| Charts | Plotly |
| Storage | JSON files with threading.RLock + atomic writes |
| Auth | bcrypt (cost factor 12) |
| Export | ReportLab (PDF) + csv module |
| Testing | Pytest (87 tests) + Selenium |
| Language | Python 3.10+ |

---

## Project Structure

```
bug_tracker/
│
├── streamlit_app.py          # ← Main entry point (Streamlit UI)
├── app.py                    # Flask REST API (legacy / reference)
│
├── modules/
│   ├── auth.py               # Registration, login, bcrypt, status transitions
│   ├── bug_manager.py        # Bug CRUD + priority scoring integration
│   ├── data_access.py        # JSON I/O layer (thread-safe, atomic writes)
│   ├── priority.py           # ctypes bridge to C priority engine
│   ├── nlp_engine.py         # TF-IDF duplicate detection + severity suggestion
│   ├── ai_summarizer.py      # Groq API summarizer with rule-based fallback
│   ├── visualizer.py         # Plotly chart builders
│   ├── report_exporter.py    # CSV + PDF export
│   ├── activity_log.py       # Audit trail helpers
│   ├── comments.py           # Comment helpers
│   ├── search_filter.py      # Search and filter logic
│   └── dashboard.py          # Dashboard stats helpers
│
├── priority_engine.c         # C source — priority score formula
├── compile.bat               # Windows: gcc compile command
├── compile.sh                # Linux/macOS: gcc compile command
│
├── data/                     # Runtime JSON storage (git-ignored)
│   ├── users.json.seed       # Empty seed — copy to users.json on setup
│   ├── bugs.json.seed
│   ├── comments.json.seed
│   └── activity_log.json.seed
│
├── static/
│   └── style.css             # Flask UI styles
│
├── templates/                # Flask Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── bug_list.html
│   ├── bug_create.html
│   ├── bug_detail.html
│   └── bug_edit.html
│
├── tests/
│   ├── conftest.py           # Pytest fixtures (tmp data dir, test client)
│   ├── test_auth.py          # 25 tests — BVA on registration/login
│   ├── test_priority.py      # 18 tests — BVA on C engine inputs
│   ├── test_bug_manager.py   # 20 tests — bug lifecycle
│   ├── test_data_access.py   # 12 tests — JSON persistence
│   └── test_selenium.py      # 12 UI tests — headless Chrome
│
├── requirements.txt
├── .env.example              # Template for API keys (copy → .env)
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- GCC / MinGW-w64 (for compiling the C priority engine)
- Google Chrome + ChromeDriver (only for Selenium tests)

### 1 — Clone the repository

```bash
git clone https://github.com/<your-username>/bug-tracker-pro.git
cd bug-tracker-pro
```

### 2 — Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 3 — Set up data files

```bash
# Windows PowerShell
copy data\users.json.seed        data\users.json
copy data\bugs.json.seed         data\bugs.json
copy data\comments.json.seed     data\comments.json
copy data\activity_log.json.seed data\activity_log.json

# Linux / macOS
cp data/users.json.seed        data/users.json
cp data/bugs.json.seed         data/bugs.json
cp data/comments.json.seed     data/comments.json
cp data/activity_log.json.seed data/activity_log.json
```

### 4 — Compile the C priority engine (optional but recommended)

```bash
# Windows
compile.bat

# Linux / macOS
bash compile.sh
```

> If you skip this step, the system automatically uses a pure-Python fallback with the same formula.

### 5 — Configure environment variables

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Then open `.env` and add your [Groq API key](https://console.groq.com) (optional — the app works without it using rule-based summaries).

---

## Running the App

### Streamlit UI (recommended)

```bash
cd bug_tracker
python -m streamlit run streamlit_app.py
```

Open → **http://localhost:8501**

### Flask API (legacy)

```bash
cd bug_tracker
python app.py
```

Open → **http://127.0.0.1:5000**

---

## Running Tests

```bash
cd bug_tracker

# Run all unit + integration tests (fast, no browser needed)
python -m pytest tests/ -v --ignore=tests/test_selenium.py

# Run Selenium UI tests (requires Chrome + running Streamlit server)
python -m pytest tests/test_selenium.py -v
```

**Test coverage summary:**

| Test File | Tests | Technique |
|---|---|---|
| `test_auth.py` | 25 | BVA, Equivalence Class Partitioning |
| `test_priority.py` | 18 | BVA on all C engine inputs |
| `test_bug_manager.py` | 20 | BVA on title/description + lifecycle |
| `test_data_access.py` | 12 | JSON persistence + atomic writes |
| `test_selenium.py` | 12 | UI automation (headless Chrome) |
| **Total** | **87** | |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Optional | Groq API key for LLaMA-3 AI summarizer. Get one free at [console.groq.com](https://console.groq.com). If not set, a rule-based fallback is used automatically. |

Create a `.env` file in the `bug_tracker/` directory (use `.env.example` as a template).  
**Never commit `.env` to version control.**

---

## User Roles

| Role | Permissions |
|---|---|
| **Admin** | Full access: create, edit, delete bugs; manage users; view all reports |
| **Developer** | View and update bug status; add comments; self-assign bugs |
| **Tester** | Report bugs; add comments; view dashboard |

---

## Bug Lifecycle

```
Open  →  In Progress  →  Resolved  →  Closed
              ↑               |
              └───────────────┘  (can reopen)
```

Status transitions are enforced server-side. Every change is recorded in the activity log.

---

## Priority Scoring

The C priority engine (`priority_engine.c`) computes a **0–100 score** using:

```
score = (severity / 4 × 40)
      + (min(age_days / 30, 1) × 35)
      + (min(related_count / 5, 1) × 25)
```

| Score Range | Label |
|---|---|
| 75 – 100 | 🔴 Critical |
| 50 – 74 | 🟠 High |
| 25 – 49 | 🟡 Medium |
| 0 – 24 | 🟢 Low |

---

## Screenshots

> *(Add screenshots of your running app here)*

| Page | Description |
|---|---|
| Login / Register | Role-based user registration |
| Report Bug | AI summarizer + duplicate detection |
| View Bugs | Filterable bug list with severity badges |
| Analytics | 5 interactive Plotly charts |
| Reports | CSV / PDF export |
| Testing Panel | UAT table + defect log |

---

## Acknowledgements

This project draws inspiration from the following industry-leading bug tracking systems:

| System | Organisation | Key Inspiration |
|---|---|---|
| [Jira](https://www.atlassian.com/software/jira) | Atlassian | Workflow customisation, priority scoring, sprint integration |
| [Bugzilla](https://www.bugzilla.org/) | Mozilla | Structured fields (severity, platform, component), CC lists |
| [GitHub Issues](https://github.com/features/issues) | GitHub | Markdown descriptions, label taxonomy, linking to commits |
| [Redmine](https://www.redmine.org/) | Open Source | Role-based access control, module/component grouping |
| [YouTrack](https://www.jetbrains.com/youtrack/) | JetBrains | AI-assisted summaries, smart search, agile boards |

---

## License

This project was developed for academic purposes under **CSL3050 — Software Engineering and Testing**, B.Tech Computer Science Engineering, Semester VI.

---

*Built with Python 🐍 | Streamlit ⚡ | C ⚙️ | Groq AI 🤖 | Plotly 📊*
