from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    try:
        member_since = datetime.fromisoformat(row["created_at"]).strftime("%B %Y")
    except (TypeError, ValueError):
        member_since = row["created_at"]

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "member_since": member_since,
    }


def _date_clause(start_date, end_date):
    sql = ""
    params = []
    if start_date:
        sql += " AND expenses.date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND expenses.date <= ?"
        params.append(end_date)
    return sql, params


# ---- [transaction history] ----

def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    date_sql, date_params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_sql + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *date_params, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]

# ---- [/transaction history] ----


# ---- [summary stats] ----

def get_summary_stats(user_id, start_date=None, end_date=None):
    date_sql, date_params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COUNT(*) AS transaction_count, COALESCE(SUM(amount), 0) AS total_spent "
            "FROM expenses WHERE user_id = ?" + date_sql,
            (user_id, *date_params),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + date_sql + " "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id, *date_params),
        ).fetchone()
    finally:
        conn.close()

    if totals["transaction_count"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": round(float(totals["total_spent"]), 2),
        "transaction_count": int(totals["transaction_count"]),
        "top_category": top["category"] if top else "—",
    }

# ---- [/summary stats] ----


# ---- [category breakdown] ----

def get_category_breakdown(user_id, start_date=None, end_date=None):
    date_sql, date_params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + date_sql + " GROUP BY category ORDER BY total DESC",
            (user_id, *date_params),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    if not grand_total:
        return []

    breakdown = [
        {
            "name": row["category"],
            "amount": round(row["total"], 2),
            "pct": int(round(row["total"] / grand_total * 100)),
        }
        for row in rows
    ]
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)

    return breakdown

# ---- [/category breakdown] ----
