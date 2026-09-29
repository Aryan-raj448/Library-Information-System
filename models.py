from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()


class Member(db.Model):
    __tablename__ = "member"

    code      = db.Column(db.String, primary_key=True)
    name      = db.Column(db.String, nullable=False)
    category  = db.Column(db.String, nullable=False)   # UG | PG | RS | FA
    join_date = db.Column(db.Date,   nullable=False, default=date.today)

    issues       = db.relationship("Issue",       backref="member", lazy=True)
    reservations = db.relationship("Reservation", backref="member", lazy=True)

    def __repr__(self):
        return f"<Member {self.code} {self.name}>"


class Book(db.Model):
    __tablename__ = "book"

    isbn             = db.Column(db.String,  primary_key=True)
    title            = db.Column(db.String,  nullable=False)
    author           = db.Column(db.String,  nullable=False)
    publisher        = db.Column(db.String)                       # optional
    rack_no          = db.Column(db.String,  nullable=False)
    total_copies     = db.Column(db.Integer, nullable=False)
    available_copies = db.Column(db.Integer, nullable=False)
    date_added       = db.Column(db.Date,    nullable=False, default=date.today)

    issues       = db.relationship("Issue",       backref="book", lazy=True)
    reservations = db.relationship("Reservation", backref="book", lazy=True)

    def __repr__(self):
        return f"<Book {self.isbn} {self.title}>"


class Issue(db.Model):
    __tablename__ = "issue"

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_isbn    = db.Column(db.String,  db.ForeignKey("book.isbn"),   nullable=False)
    member_code  = db.Column(db.String,  db.ForeignKey("member.code"), nullable=False)
    issue_date   = db.Column(db.Date,    nullable=False)
    due_date     = db.Column(db.Date,    nullable=False)
    return_date  = db.Column(db.Date)          # NULL until returned
    penalty_paid = db.Column(db.Float,   nullable=False, default=0.0)

    def __repr__(self):
        return f"<Issue {self.id} {self.member_code} -> {self.book_isbn}>"


class Reservation(db.Model):
    __tablename__ = "reservation"

    id               = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_isbn        = db.Column(db.String,  db.ForeignKey("book.isbn"),   nullable=False)
    member_code      = db.Column(db.String,  db.ForeignKey("member.code"), nullable=False)
    reservation_date = db.Column(db.Date,    nullable=False)
    status           = db.Column(db.String,  nullable=False)  # Waiting | Hold | Fulfilled | Expired
    hold_until       = db.Column(db.Date)    # NULL unless status == 'Hold'

    def __repr__(self):
        return f"<Reservation {self.id} {self.member_code} -> {self.book_isbn} [{self.status}]>"

