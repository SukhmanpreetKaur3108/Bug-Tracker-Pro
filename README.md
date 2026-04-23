# Bug Tracker Pro 🐛

An AI-enhanced bug tracking and defect management system built with Python and Streamlit.

---

## What it does

- Report and track software bugs with severity, priority, and status
- AI-powered bug summarizer (Groq / LLaMA-3) with a rule-based fallback
- NLP duplicate detection using TF-IDF cosine similarity
- C-powered priority scoring engine (0–100 score)
- Interactive analytics dashboard with Plotly charts
- Export bug reports as CSV or PDF
- Role-based access: Admin, Developer, Tester
- Full audit trail and comment system

---

## Tech Stack

- **UI:** Streamlit
- **Priority Engine:** C + Python ctypes
- **NLP:** scikit-learn
- **AI:** Groq API (LLaMA-3)
- **Charts:** Plotly
- **Storage:** JSON files
- **Auth:** bcrypt
- **Testing:** Pytest + Selenium

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/<your-username>/bug-tracker-pro.git
cd bug-tracker-pro
```

**2. Install dependencies**
```bash
python -m pip install -r requirements.txt
```

**3. Set up data files**
```bash
# Windows
copy data\users.json.seed        data\users.json
copy data\bugs.json.seed         data\bugs.json
copy data\comments.json.seed     data\comments.json
copy data\activity_log.json.seed data\activity_log.json
```

**4. Compile the C priority engine** *(optional — Python fallback is used if skipped)*
```bash
compile.bat        # Windows
bash compile.sh    # Linux / macOS
```

**5. Set up your API key** *(optional — app works without it)*
```bash
copy .env.example .env   # then add your Groq API key inside
```

---

## Run the App

```bash
python -m streamlit run streamlit_app.py
```

Open → **http://localhost:8501**

---

## Run Tests

```bash
python -m pytest tests/ -v --ignore=tests/test_selenium.py
```

87 tests covering authentication, bug lifecycle, priority engine, and JSON storage.

---

## User Roles

| Role | Can Do |
|---|---|
| Admin | Everything — create, edit, delete, assign, manage users |
| Developer | Update status, add comments, self-assign bugs |
| Tester | Report bugs, add comments, view dashboard |

---

## Project Structure

```
bug_tracker/
├── streamlit_app.py       # Main UI
├── app.py                 # Flask API (legacy)
├── priority_engine.c      # C priority score formula
├── modules/               # Core logic (auth, bugs, NLP, AI, charts...)
├── templates/             # Flask HTML templates
├── static/                # CSS
├── tests/                 # Pytest + Selenium test suite
├── data/                  # JSON storage (git-ignored)
└── requirements.txt
```

---

## Inspired by

Jira · Bugzilla · GitHub Issues · Redmine · YouTrack

---

*CSL3050 — Software Engineering and Testing | B.Tech CS, Semester VI*
