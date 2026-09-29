"""
seed.py -- Populate lis.db with demo data.

Run once:
    python seed.py

Safe to re-run: skips rows that already exist.
"""

from datetime import date, timedelta
from app import app, db
from models import Member, Book, Issue, Reservation


def seed():
    with app.app_context():
        db.create_all()

        # -- Members ---------------------------------------------------------
        members = [
            Member(code="U001", name="Arjun Mehta",     category="UG", join_date=date(2024, 7, 1)),
            Member(code="U002", name="Priya Nair",       category="UG", join_date=date(2024, 7, 1)),
            Member(code="U003", name="Rahul Singh",      category="UG", join_date=date(2024, 8, 1)),
            Member(code="P001", name="Sneha Rao",        category="PG", join_date=date(2023, 6, 15)),
            Member(code="P002", name="Vikram Joshi",     category="PG", join_date=date(2023, 6, 15)),
            Member(code="R001", name="Dr. Kavita Desai", category="RS", join_date=date(2022, 1, 10)),
            Member(code="R002", name="Anand Krishnan",   category="RS", join_date=date(2022, 3, 20)),
            Member(code="F001", name="Prof. Sharma",     category="FA", join_date=date(2018, 4, 1)),
            Member(code="F002", name="Prof. Iyer",       category="FA", join_date=date(2019, 6, 1)),
        ]
        for m in members:
            if not db.session.get(Member, m.code):
                db.session.add(m)

        # -- Books -----------------------------------------------------------
        books = [
            Book(isbn="978-0-13-110362-7", title="The C Programming Language",
                 author="Kernighan & Ritchie", publisher="Prentice Hall",
                 rack_no="CS-A1", total_copies=4, available_copies=4,
                 date_added=date(2020, 1, 15)),

            Book(isbn="978-0-13-468599-1", title="Clean Code",
                 author="Robert C. Martin", publisher="Prentice Hall",
                 rack_no="CS-A2", total_copies=3, available_copies=3,
                 date_added=date(2021, 3, 10)),

            Book(isbn="978-0-201-63361-0", title="Design Patterns",
                 author="Gang of Four", publisher="Addison-Wesley",
                 rack_no="CS-B1", total_copies=2, available_copies=2,
                 date_added=date(2019, 6, 5)),

            Book(isbn="978-0-13-235088-4", title="Introduction to Algorithms",
                 author="Cormen et al.", publisher="MIT Press",
                 rack_no="CS-B2", total_copies=5, available_copies=5,
                 date_added=date(2020, 8, 20)),

            Book(isbn="978-0-596-51774-8", title="Learning Python",
                 author="Mark Lutz", publisher="O'Reilly",
                 rack_no="CS-C1", total_copies=3, available_copies=3,
                 date_added=date(2022, 2, 1)),

            Book(isbn="978-1-491-91205-8", title="Flask Web Development",
                 author="Miguel Grinberg", publisher="O'Reilly",
                 rack_no="CS-C2", total_copies=2, available_copies=2,
                 date_added=date(2023, 5, 15)),

            Book(isbn="978-0-07-352332-3", title="Database System Concepts",
                 author="Silberschatz et al.", publisher="McGraw-Hill",
                 rack_no="CS-D1", total_copies=4, available_copies=4,
                 date_added=date(2018, 9, 1)),

            Book(isbn="978-0-13-292401-7", title="Computer Networks",
                 author="Tanenbaum", publisher="Pearson",
                 rack_no="CS-D2", total_copies=3, available_copies=3,
                 date_added=date(2017, 11, 1)),     # old -- will appear in unused report

            Book(isbn="978-0-321-12521-7", title="Domain-Driven Design",
                 author="Eric Evans", publisher="Addison-Wesley",
                 rack_no="CS-E1", total_copies=1, available_copies=1,
                 date_added=date(2016, 4, 10)),     # old -- will appear in unused report

            Book(isbn="978-0-13-110362-0", title="Operating System Concepts",
                 author="Silberschatz et al.", publisher="Wiley",
                 rack_no="CS-E2", total_copies=3, available_copies=3,
                 date_added=date(2021, 7, 1)),
        ]
        for b in books:
            if not db.session.get(Book, b.isbn):
                db.session.add(b)

        db.session.commit()   # commit members + books before FK references

        # -- Issues ----------------------------------------------------------
        today = date.today()

        issues = [
            # On-time, returned
            Issue(book_isbn="978-0-13-110362-7", member_code="U001",
                  issue_date=today - timedelta(days=40),
                  due_date=today  - timedelta(days=10),
                  return_date=today - timedelta(days=12),
                  penalty_paid=0.0),

            # Overdue -- still out (will show in reminders)
            Issue(book_isbn="978-0-13-468599-1", member_code="U002",
                  issue_date=today - timedelta(days=50),
                  due_date=today  - timedelta(days=20),
                  return_date=None,
                  penalty_paid=0.0),

            # Overdue -- still out (UG at limit: 2 books)
            Issue(book_isbn="978-0-201-63361-0", member_code="U002",
                  issue_date=today - timedelta(days=35),
                  due_date=today  - timedelta(days=5),
                  return_date=None,
                  penalty_paid=0.0),

            # PG -- current, on time
            Issue(book_isbn="978-0-13-235088-4", member_code="P001",
                  issue_date=today - timedelta(days=10),
                  due_date=today  + timedelta(days=20),
                  return_date=None,
                  penalty_paid=0.0),

            # RS -- recent issue
            Issue(book_isbn="978-0-596-51774-8", member_code="R001",
                  issue_date=today - timedelta(days=5),
                  due_date=today  + timedelta(days=85),
                  return_date=None,
                  penalty_paid=0.0),

            # FA -- issue so Operating System Concepts has available_copies = 2
            Issue(book_isbn="978-0-13-110362-0", member_code="F001",
                  issue_date=today - timedelta(days=20),
                  due_date=today  + timedelta(days=160),
                  return_date=None,
                  penalty_paid=0.0),
        ]
        for iss in issues:
            exists = Issue.query.filter_by(
                member_code=iss.member_code,
                book_isbn=iss.book_isbn,
                return_date=iss.return_date
            ).first()
            if not exists:
                db.session.add(iss)
                # Keep available_copies consistent for open loans
                if iss.return_date is None:
                    book = db.session.get(Book, iss.book_isbn)
                    if book and book.available_copies > 0:
                        book.available_copies -= 1

        # -- Reservation -----------------------------------------------------
        # U003 has reserved Clean Code (which U002 has out on loan)
        book_clean_code = db.session.get(Book, "978-0-13-468599-1")
        if book_clean_code and book_clean_code.available_copies < book_clean_code.total_copies:
            existing_res = Reservation.query.filter_by(
                book_isbn="978-0-13-468599-1",
                member_code="U003",
                status="Waiting"
            ).first()
            if not existing_res:
                db.session.add(Reservation(
                    book_isbn="978-0-13-468599-1",
                    member_code="U003",
                    reservation_date=today - timedelta(days=3),
                    status="Waiting",
                    hold_until=None,
                ))

        db.session.commit()
        print("[OK] Seed complete.")
        print("   Members      :", Member.query.count())
        print("   Books        :", Book.query.count())
        print("   Issues       :", Issue.query.count())
        print("   Reservations :", Reservation.query.count())


if __name__ == "__main__":
    seed()

