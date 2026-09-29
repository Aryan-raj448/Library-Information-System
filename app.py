import os
from datetime import date, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort, send_from_directory
)
from models import db, Member, Book, Issue, Reservation

# Load environment variables from .env
load_dotenv()

# ─────────────────────────────────────────────
#  App setup
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("LIS_SECRET", "lis-dev-secret-change-me")

# Check for Supabase / PostgreSQL database URL
database_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("SUPABASE_DATABASE_URL")
    or os.environ.get("SUPABASE_DB_URL")
)

if database_url:
    # Normalize postgres:// prefix to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # If postgresql:// is provided without an explicit driver, ensure compatibility
    if database_url.startswith("postgresql://") and not database_url.startswith("postgresql+"):
        try:
            import psycopg
        except ImportError:
            try:
                import psycopg2
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            except ImportError:
                pass

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'lis.db')}"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# ─────────────────────────────────────────────
#  Business-rule constants
# ─────────────────────────────────────────────
CATEGORY_LIMITS = {
    "UG": {"books": 2,  "days": 30},
    "PG": {"books": 4,  "days": 30},
    "RS": {"books": 6,  "days": 90},
    "FA": {"books": 10, "days": 180},
}
FINE_PER_DAY = 2      # Rs. 2
HOLD_DAYS    = 7
UNUSED_YEARS = 5

# ─────────────────────────────────────────────
#  Reservation hold-expiry — runs before every request
# ─────────────────────────────────────────────
@app.before_request
def expire_holds():
    """Expire any Hold whose hold_until date has passed, then cascade."""
    today = date.today()
    expired_holds = Reservation.query.filter(
        Reservation.status == "Hold",
        Reservation.hold_until < today
    ).all()

    for res in expired_holds:
        res.status = "Expired"
        next_waiting = (
            Reservation.query
            .filter_by(book_isbn=res.book_isbn, status="Waiting")
            .order_by(Reservation.reservation_date)
            .first()
        )
        if next_waiting:
            next_waiting.status     = "Hold"
            next_waiting.hold_until = today + timedelta(days=HOLD_DAYS)
        else:
            book = db.session.get(Book, res.book_isbn)
            if book:
                book.available_copies += 1

    if expired_holds:
        db.session.commit()


# ─────────────────────────────────────────────
#  Auth helpers
# ─────────────────────────────────────────────
STAFF_ROLES = {"librarian", "clerk"}


def get_session_role():
    return session.get("role")


def is_member_session():
    role = get_session_role()
    return role and role not in STAFF_ROLES


def require_role(*allowed_roles):
    """Decorator that enforces role-based access. Returns 403 otherwise."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            role = get_session_role()
            if role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_member():
    """Decorator for member-only routes (any member code in session)."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not is_member_session():
                abort(403)
            member = db.session.get(Member, get_session_role())
            if not member:
                session.clear()
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_logged_in():
    """Decorator that just ensures any session exists."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not get_session_role():
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ─────────────────────────────────────────────
#  Context processor — inject role into every template
# ─────────────────────────────────────────────
@app.context_processor
def inject_role():
    role = get_session_role()
    member = None
    if is_member_session():
        member = db.session.get(Member, role)
    return dict(session_role=role, session_member=member)


# ─────────────────────────────────────────────
#  FR1  /login  /logout
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        if role in ("librarian", "clerk"):
            session["role"] = role
            return redirect(url_for("search"))
        if role:
            member = db.session.get(Member, role.upper())
            if member:
                session["role"] = member.code
                return redirect(url_for("search"))
            flash("Member code not found.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
#  FR4  /search  (all roles)
# ─────────────────────────────────────────────
@app.route("/search")
@require_logged_in()
def search():
    q = request.args.get("q", "").strip()
    books = []
    if q:
        like = f"%{q}%"
        books = Book.query.filter(
            db.or_(
                Book.isbn.like(like),
                Book.title.like(like),
                Book.author.like(like),
            )
        ).all()
    return render_template("books/search.html", books=books, q=q)


# ─────────────────────────────────────────────
#  FR2  /books/add  (clerk)
# ─────────────────────────────────────────────
@app.route("/books/add", methods=["GET", "POST"])
@require_role("clerk")
def books_add():
    if request.method == "POST":
        isbn      = request.form["isbn"].strip()
        title     = request.form["title"].strip()
        author    = request.form["author"].strip()
        publisher = request.form.get("publisher", "").strip()
        rack_no   = request.form["rack_no"].strip()
        copies    = int(request.form["copies"])

        if db.session.get(Book, isbn):
            flash("Book with this ISBN already exists.", "danger")
        elif copies < 1:
            flash("Copies must be at least 1.", "danger")
        else:
            book = Book(
                isbn=isbn, title=title, author=author,
                publisher=publisher or None,
                rack_no=rack_no,
                total_copies=copies, available_copies=copies,
                date_added=date.today()
            )
            db.session.add(book)
            db.session.commit()
            flash(f"Book '{title}' added successfully.", "success")
            return redirect(url_for("search"))
    return render_template("books/add.html")


# ─────────────────────────────────────────────
#  FR3  /books/delete  (clerk)
# ─────────────────────────────────────────────
@app.route("/books/delete", methods=["GET", "POST"])
@require_role("clerk")
def books_delete():
    book = None
    if request.method == "POST":
        action = request.form.get("action")
        isbn   = request.form.get("isbn", "").strip()

        if action == "lookup":
            book = db.session.get(Book, isbn)
            if not book:
                flash("No book found with that ISBN.", "danger")

        elif action == "confirm":
            book = db.session.get(Book, isbn)
            if not book:
                flash("Book not found.", "danger")
            elif book.available_copies != book.total_copies:
                flash("Cannot delete: one or more copies are currently on loan.", "danger")
                return render_template("books/delete.html", book=book)
            else:
                db.session.delete(book)
                db.session.commit()
                flash(f"Book '{book.title}' deleted.", "success")
                return redirect(url_for("search"))

    return render_template("books/delete.html", book=book)


# ─────────────────────────────────────────────
#  FR5  /members  (librarian)
# ─────────────────────────────────────────────
@app.route("/members", methods=["GET", "POST"])
@require_role("librarian")
def members():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            code     = request.form["code"].strip().upper()
            name     = request.form["name"].strip()
            category = request.form["category"].strip()

            if db.session.get(Member, code):
                flash("A member with that code already exists.", "danger")
            elif category not in CATEGORY_LIMITS:
                flash("Invalid category.", "danger")
            else:
                m = Member(code=code, name=name, category=category,
                           join_date=date.today())
                db.session.add(m)
                db.session.commit()
                flash(f"Member '{name}' registered.", "success")

        elif action == "remove":
            code = request.form["remove_code"].strip().upper()
            m = db.session.get(Member, code)
            if not m:
                flash("Member not found.", "danger")
            else:
                open_issues = Issue.query.filter_by(
                    member_code=code, return_date=None
                ).count()
                if open_issues:
                    flash("Cannot remove: member has unreturned books.", "danger")
                else:
                    db.session.delete(m)
                    db.session.commit()
                    flash(f"Member '{m.name}' removed.", "success")

    all_members = Member.query.order_by(Member.code).all()
    return render_template("members/index.html", members=all_members,
                           categories=list(CATEGORY_LIMITS.keys()))


# ─────────────────────────────────────────────
#  FR6  /issue  (clerk)
# ─────────────────────────────────────────────
@app.route("/issue", methods=["GET", "POST"])
@require_role("clerk")
def issue():
    if request.method == "POST":
        member_code = request.form["member_code"].strip().upper()
        isbn        = request.form["isbn"].strip()

        member = db.session.get(Member, member_code)
        if not member:
            flash("Member not found.", "danger")
            return render_template("issue.html")

        book = db.session.get(Book, isbn)
        if not book:
            flash("Book not found.", "danger")
            return render_template("issue.html")

        # 1. Check category limit
        open_count = Issue.query.filter_by(
            member_code=member_code, return_date=None
        ).count()
        limit = CATEGORY_LIMITS[member.category]["books"]
        if open_count >= limit:
            flash(f"Member has reached the issue limit ({limit} books for {member.category}).", "danger")
            return render_template("issue.html")

        # 2. Check hold — reserved for someone else?
        hold = (
            Reservation.query
            .filter_by(book_isbn=isbn, status="Hold")
            .first()
        )
        if hold and hold.member_code != member_code:
            flash("Book is reserved by another member and is currently on hold.", "danger")
            return render_template("issue.html")

        # 3. Availability
        if book.available_copies < 1:
            flash("No copies available.", "danger")
            return render_template("issue.html")

        # 4. Create issue record
        due_date = date.today() + timedelta(days=CATEGORY_LIMITS[member.category]["days"])
        new_issue = Issue(
            book_isbn=isbn,
            member_code=member_code,
            issue_date=date.today(),
            due_date=due_date,
        )
        book.available_copies -= 1

        # 5. Fulfil hold if this member was the one holding
        if hold and hold.member_code == member_code:
            hold.status = "Fulfilled"

        db.session.add(new_issue)
        db.session.commit()
        flash(
            f"Book issued to {member.name}. Due date: {due_date.strftime('%d %b %Y')}.",
            "success"
        )
        return redirect(url_for("issue"))

    return render_template("issue.html")


# ─────────────────────────────────────────────
#  FR7  /return  (clerk)
# ─────────────────────────────────────────────
@app.route("/return", methods=["GET", "POST"])
@require_role("clerk")
def book_return():
    if request.method == "POST":
        member_code = request.form["member_code"].strip().upper()
        isbn        = request.form["isbn"].strip()

        open_issue = (
            Issue.query
            .filter_by(member_code=member_code, book_isbn=isbn, return_date=None)
            .first()
        )
        if not open_issue:
            flash("No open issue found for that member and book.", "danger")
            return render_template("return.html")

        today = date.today()
        open_issue.return_date = today

        overdue_days = (today - open_issue.due_date).days
        penalty = max(0, overdue_days) * FINE_PER_DAY
        open_issue.penalty_paid = penalty

        book = db.session.get(Book, isbn)

        next_res = (
            Reservation.query
            .filter_by(book_isbn=isbn, status="Waiting")
            .order_by(Reservation.reservation_date)
            .first()
        )

        if next_res:
            next_res.status     = "Hold"
            next_res.hold_until = today + timedelta(days=HOLD_DAYS)
            reserved_member = db.session.get(Member, next_res.member_code)
            db.session.commit()
            return render_template(
                "slip.html",
                issue=open_issue,
                book=book,
                penalty=penalty,
                reserved_member=reserved_member,
                hold_until=next_res.hold_until,
            )
        else:
            book.available_copies += 1
            db.session.commit()
            return render_template(
                "return.html",
                done=True,
                issue=open_issue,
                book=book,
                penalty=penalty,
            )

    return render_template("return.html")


# ─────────────────────────────────────────────
#  FR8  /reserve  (member)
# ─────────────────────────────────────────────
@app.route("/reserve", methods=["GET", "POST"])
@require_member()
def reserve():
    member_code = get_session_role()
    if request.method == "POST":
        isbn = request.form["isbn"].strip()

        book = db.session.get(Book, isbn)
        if not book:
            flash("Book not found.", "danger")
            return render_template("reserve.html")

        if book.available_copies > 0:
            flash("Book is currently available — visit the desk to borrow it directly.", "info")
            return render_template("reserve.html")

        existing = (
            Reservation.query
            .filter_by(book_isbn=isbn, member_code=member_code)
            .filter(Reservation.status.in_(["Waiting", "Hold"]))
            .first()
        )
        if existing:
            flash("You already have an active reservation for this book.", "warning")
            return render_template("reserve.html")

        res = Reservation(
            book_isbn=isbn,
            member_code=member_code,
            reservation_date=date.today(),
            status="Waiting",
        )
        db.session.add(res)
        db.session.commit()
        flash(f"Reservation placed for '{book.title}'. You are in the queue.", "success")
        return redirect(url_for("search"))

    return render_template("reserve.html")


# ─────────────────────────────────────────────
#  FR9  /reports/reminders  (librarian)
# ─────────────────────────────────────────────
@app.route("/reports/reminders")
@require_role("librarian")
def reports_reminders():
    today = date.today()
    overdue = (
        Issue.query
        .filter(Issue.return_date.is_(None), Issue.due_date < today)
        .order_by(Issue.due_date)
        .all()
    )
    return render_template("reports/reminders.html", overdue=overdue, today=today)


# ─────────────────────────────────────────────
#  FR10  /reports/unused  (librarian)
# ─────────────────────────────────────────────
@app.route("/reports/unused")
@require_role("librarian")
def reports_unused():
    cutoff = date.today().replace(year=date.today().year - UNUSED_YEARS)
    active_book_isbns = (
        db.session.query(Issue.book_isbn)
        .filter(Issue.issue_date >= cutoff)
        .distinct()
        .subquery()
    )
    unused_books = (
        Book.query
        .filter(~Book.isbn.in_(active_book_isbns))
        .order_by(Book.title)
        .all()
    )
    return render_template("reports/unused.html", books=unused_books, cutoff=cutoff)


# ─────────────────────────────────────────────
#  Error handlers
# ─────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

