import pytest

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)
from database.db import get_user_by_email


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def register_and_login(client, name="New User", email="new@example.com", password="password123"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    return login(client, email=email, password=password)


def demo_id():
    return get_user_by_email("demo@spendly.com")["id"]


def new_user_id(client):
    register_and_login(client)
    return get_user_by_email("new@example.com")["id"]


def test_get_user_by_id_valid(app):
    user = get_user_by_id(demo_id())
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    month, year = user["member_since"].split()
    assert year.isdigit() and len(year) == 4
    assert month.isalpha()


def test_get_user_by_id_unknown(app):
    assert get_user_by_id(9999) is None


# ---- [transaction history] ----

def test_recent_transactions_newest_first(app):
    items = get_recent_transactions(demo_id())
    assert len(items) == 8
    for item in items:
        assert set(item.keys()) == {"date", "description", "category", "amount"}
    dates = [item["date"] for item in items]
    assert dates == sorted(dates, reverse=True)
    assert items[0]["description"] == "Groceries"
    assert items[-1]["description"] == "Lunch"


def test_recent_transactions_limit(app):
    assert len(get_recent_transactions(demo_id(), limit=3)) == 3


def test_recent_transactions_empty_for_new_user(client):
    assert get_recent_transactions(new_user_id(client)) == []


# ---- [/transaction history] ----


# ---- [summary stats] ----

def test_summary_stats_demo_user(app):
    stats = get_summary_stats(demo_id())
    assert stats["total_spent"] == pytest.approx(330.78)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_empty_for_new_user(client):
    assert get_summary_stats(new_user_id(client)) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }

# ---- [/summary stats] ----


# ---- [category breakdown] ----

def test_category_breakdown_demo_user(app):
    breakdown = get_category_breakdown(demo_id())
    assert len(breakdown) == 7
    for item in breakdown:
        assert set(item.keys()) == {"name", "amount", "pct"}
        assert isinstance(item["pct"], int)
    amounts = [item["amount"] for item in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert breakdown[0]["name"] == "Bills"
    assert sum(item["pct"] for item in breakdown) == 100


def test_category_breakdown_empty_for_new_user(client):
    assert get_category_breakdown(new_user_id(client)) == []

# ---- [/category breakdown] ----


def test_profile_route_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_route_demo_user(client):
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Demo User" in page
    assert "demo@spendly.com" in page
    assert "₹330.78" in page
    assert '<span class="stat-value">8</span>' in page
    assert '<span class="stat-value">Bills</span>' in page
    assert page.index("Groceries") < page.index("Lunch")
    assert page.count('class="category-row"') == 7
    assert "style=" not in page.split('<section class="profile-section">')[1]


def test_profile_route_new_user(client):
    register_and_login(client)
    page = client.get("/profile").get_data(as_text=True)
    assert "₹0.00" in page
    assert '<span class="stat-value">0</span>' in page
    assert '<span class="stat-value">—</span>' in page
    assert 'class="category-row"' not in page
