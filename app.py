import os
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


def _is_valid_email(email):
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or not domain:
        return False
    return "." in domain[1:-1]


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not name or not email or not password:
        error = "All fields are required."
    elif not _is_valid_email(email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif get_user_by_email(email) is not None:
        error = "An account with that email already exists."

    if error is None:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "An account with that email already exists."

    if error:
        return render_template("register.html", error=error, name=name, email=email), 400

    flash("Account created — please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.", email=email), 400

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email), 401

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


def _format_date(value, fmt):
    try:
        return datetime.fromisoformat(value).strftime(fmt)
    except (TypeError, ValueError):
        return value


# ---- [transaction history] ----

def _transaction_history(user_id, start_date=None, end_date=None):
    return [
        {**row, "display_date": _format_date(row["date"], "%d %b %Y")}
        for row in get_recent_transactions(
            user_id, start_date=start_date, end_date=end_date
        )
    ]

# ---- [/transaction history] ----


# ---- [summary stats] ----

def _summary_stats(user_id, start_date=None, end_date=None):
    return get_summary_stats(user_id, start_date=start_date, end_date=end_date)

# ---- [/summary stats] ----


# ---- [category breakdown] ----

def _category_breakdown(user_id, start_date=None, end_date=None):
    return get_category_breakdown(user_id, start_date=start_date, end_date=end_date)

# ---- [/category breakdown] ----


# ---- [date filter] ----

DATE_PRESETS = {
    "this-month": "This month",
    "last-month": "Last month",
    "last-3-months": "Last 3 months",
    "all": "All time",
}


def _parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value)


def _first_of_month(today, months_back):
    index = today.year * 12 + today.month - 1 - months_back
    return date(index // 12, index % 12 + 1, 1)


def _preset_bounds(key, today):
    if key == "this-month":
        return _first_of_month(today, 0), today
    if key == "last-month":
        last = _first_of_month(today, 0) - timedelta(days=1)
        return _first_of_month(today, 1), last
    if key == "last-3-months":
        return _first_of_month(today, 2), today
    return None, None


def _resolve_filter(args):
    key = args.get("range", "")
    if key in DATE_PRESETS:
        start, end = _preset_bounds(key, date.today())
        return start, end, key, None

    try:
        start = _parse_date(args.get("start"))
        end = _parse_date(args.get("end"))
    except ValueError:
        return None, None, "all", "Invalid date — showing all expenses."

    if start and end and start > end:
        return None, None, "all", "Start date must be before end date."

    # A custom range highlights no preset; an empty one is the same as "All time".
    active_range = None if (start or end) else "all"
    return start, end, active_range, None


def _period_label(start, end):
    fmt = "%d %b %Y"
    if start and end:
        return f"Showing {start.strftime(fmt)} – {end.strftime(fmt)}"
    if start:
        return f"Showing from {start.strftime(fmt)}"
    if end:
        return f"Showing up to {end.strftime(fmt)}"
    return "Showing all time"


def _has_any_expenses(user_id, summary, is_filtered):
    if summary["transaction_count"] > 0:
        return True
    if not is_filtered:
        return False
    return _summary_stats(user_id)["transaction_count"] > 0

# ---- [/date filter] ----


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    start, end, active_range, error = _resolve_filter(request.args)
    if error:
        flash(error, "error")

    start_date = start.isoformat() if start else None
    end_date = end.isoformat() if end else None

    summary = _summary_stats(user_id, start_date, end_date)

    return render_template(
        "profile.html",
        user=user,
        member_since=user["member_since"],
        summary=summary,
        recent=_transaction_history(user_id, start_date, end_date),
        categories=_category_breakdown(user_id, start_date, end_date),
        start=start_date or "",
        end=end_date or "",
        presets=DATE_PRESETS,
        active_range=active_range,
        period_label=_period_label(start, end),
        has_any_expenses=_has_any_expenses(user_id, summary, bool(start or end)),
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
