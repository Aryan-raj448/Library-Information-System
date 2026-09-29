# Library Information System (LIS)

A single-branch library management web application built with **Python · Flask · SQLAlchemy · Supabase (PostgreSQL) / SQLite · Bootstrap 5**.

---

## Features

| Module | What it does |
|---|---|
| **Authentication** | Three roles — Librarian, Clerk, Member (sign-in by member code) |
| **Book Catalogue** | Add, search (ISBN / title / author), delete with loan guard |
| **Member Management** | Register and remove members across 4 categories (UG, PG, RS, FA) |
| **Issue & Return** | Enforce per-category limits; compute overdue fines at Rs. 2/day |
| **Reservations** | FIFO queue; 7-day hold on return; auto-expire cascade |
| **Reports** | Printable overdue reminders and unused-books (5-year) report |

---

## Quick Start

### Prerequisites
- Python 3.10+

### Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd lis-swe

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional — defaults work for dev)
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
# Edit .env and set LIS_SECRET to a strong random string

# 5. Seed demo data (optional but recommended)
python seed.py

# 6. Run the development server
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

---

## Sign-in Guide

| Role | How to sign in |
|---|---|
| Librarian | Click **Sign in as Librarian** |
| Clerk | Click **Sign in as Clerk** |
| Member | Type your member code (e.g. `U001`) |

### Demo member codes (after running `seed.py`)

| Code | Name | Category | Notes |
|---|---|---|---|
| `U001` | Arjun Mehta | UG | 1 returned book |
| `U002` | Priya Nair | UG | **2 overdue books** (at limit) |
| `U003` | Rahul Singh | UG | Waiting reservation on *Clean Code* |
| `P001` | Sneha Rao | PG | 1 active issue |
| `R001` | Dr. Kavita Desai | RS | 1 active issue |
| `F001` | Prof. Sharma | FA | 1 active issue |

---

## Project Structure

```
lis-swe/
├── app.py              # Flask app — all routes and business logic
├── models.py           # SQLAlchemy ORM models
├── seed.py             # Demo data loader
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore
└── templates/
    ├── base.html           # Bootstrap 5 layout + print CSS
    ├── login.html
    ├── issue.html
    ├── return.html         # + printable penalty receipt
    ├── slip.html           # Printable reservation slip
    ├── reserve.html
    ├── books/
    │   ├── add.html
    │   ├── delete.html
    │   └── search.html
    ├── members/
    │   └── index.html
    └── reports/
        ├── reminders.html  # Printable overdue list
        └── unused.html     # 5-year unused-books report
```

---

## Business Rules

| Rule | Value |
|---|---|
| UG book limit | 2 books / 30-day loan |
| PG book limit | 4 books / 30-day loan |
| RS book limit | 6 books / 90-day loan |
| FA book limit | 10 books / 180-day loan |
| Overdue fine | Rs. 2 per day |
| Reservation hold | 7 days |
| Unused-book threshold | No issue in 5 years |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x |
| ORM | Flask-SQLAlchemy 3.x |
| Database | SQLite (`lis.db`) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |
| Templating | Jinja2 (server-side rendering) |

---

## Security

- All database queries go through SQLAlchemy (parameterized — no SQL injection)
- Role checks enforced server-side; unauthorized access returns HTTP 403
- Secret key loaded from `LIS_SECRET` environment variable

---

## License

This project was built as a software engineering coursework submission.
