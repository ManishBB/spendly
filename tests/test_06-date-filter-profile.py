"""Tests for Spendly feature 06 - Date Filter for the Profile page.

Written against .claude/specs/06-date-filter-profile.md.
Seed data: demo user (id 1) has 8 expenses on days 1,3,6,9,12,15,19,24 of the
current month, totalling 330.78.
"""
from datetime import date, timedelta

import pytest

import database.db as db
from app import _preset_bounds
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)

TODAY = date.today()
SEED_MONTH = f"{TODAY:%Y-%m}"

# (day, amount, category, description)
SEED = [
    (1, 12.50, "Food", "Lunch"),
    (3, 45.00, "Transport", "Monthly bus pass"),
    (6, 89.99, "Bills", "Electricity bill"),
    (9, 25.00, "Health", "Pharmacy"),
    (12, 15.99, "Entertainment", "Movie night"),
    (15, 60.00, "Shopping", "New shoes"),
    (19, 10.00, "Other", "Gift wrap"),
    (24, 72.30, "Food", "Groceries"),
]
ALL_DESCRIPTIONS = [s[3] for s in SEED]


def _seed_d(day):
    return f"{SEED_MONTH}-{day:02d}"


def _month_shift(d, months_back):
    """First day of the month `months_back` months before d's month."""
    idx = d.year * 12 + (d.month - 1) - months_back
    return date(idx // 12, idx % 12 + 1, 1)


# --------------------------------------------------------------------- #
# Fixtures / helpers                                                    #
# --------------------------------------------------------------------- #

@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def demo_client(client):
    resp = client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    assert resp.status_code == 302, "Demo login should redirect"
    return client


def _add_expense(user_id, amount, category, iso_date, description):
    conn = db.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, iso_date, description),
        )
        conn.commit()
    finally:
        conn.close()


def _db_snapshot():
    conn = db.get_db()
    try:
        rows = conn.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses ORDER BY id"
        ).fetchall()
        return [tuple(r) for r in rows]
    finally:
        conn.close()


def _second_user_client(app, email="other@example.com", password="otherpass123"):
    c = app.test_client()
    r = c.post("/register", data={"name": "Other", "email": email, "password": password})
    assert r.status_code == 302, "Registration should redirect to login"
    r = c.post("/login", data={"email": email, "password": password})
    assert r.status_code == 302, "Second user login should redirect"
    conn = db.get_db()
    try:
        uid = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
    finally:
        conn.close()
    return c, uid


def _text(resp):
    return resp.get_data(as_text=True)


def _expected_this_month():
    rows = [s for s in SEED if s[0] <= TODAY.day]
    return rows, round(sum(s[1] for s in rows), 2)


# --------------------------------------------------------------------- #
# Query helpers                                                         #
# --------------------------------------------------------------------- #

class TestQueryHelpers:
    def test_summary_no_dates_returns_all_time(self, app):
        s = get_summary_stats(1)
        assert s["transaction_count"] == 8
        assert s["total_spent"] == pytest.approx(330.78)

    def test_summary_range_middle(self, app):
        s = get_summary_stats(1, start_date=_seed_d(10), end_date=_seed_d(20))
        assert s["transaction_count"] == 3
        assert s["total_spent"] == pytest.approx(85.99)
        assert s["top_category"] == "Shopping"

    def test_summary_start_only(self, app):
        s = get_summary_stats(1, start_date=_seed_d(20))
        assert s["transaction_count"] == 1
        assert s["total_spent"] == pytest.approx(72.30)

    def test_summary_end_only(self, app):
        s = get_summary_stats(1, end_date=_seed_d(5))
        assert s["transaction_count"] == 2
        assert s["total_spent"] == pytest.approx(57.50)

    def test_summary_bounds_are_inclusive(self, app):
        s = get_summary_stats(1, start_date=_seed_d(12), end_date=_seed_d(12))
        assert s["transaction_count"] == 1
        assert s["total_spent"] == pytest.approx(15.99)
        s = get_summary_stats(1, start_date=_seed_d(12), end_date=_seed_d(15))
        assert s["transaction_count"] == 2

    def test_summary_empty_range(self, app):
        s = get_summary_stats(1, start_date="1999-01-01", end_date="1999-12-31")
        assert s["transaction_count"] == 0
        assert s["total_spent"] == 0
        assert s["top_category"] == "—"

    def test_recent_transactions_filtered(self, app):
        rows = get_recent_transactions(1, start_date=_seed_d(10), end_date=_seed_d(20))
        assert sorted(r["description"] for r in rows) == ["Gift wrap", "Movie night", "New shoes"]

    def test_recent_transactions_start_only_and_end_only(self, app):
        late = get_recent_transactions(1, start_date=_seed_d(20))
        assert [r["description"] for r in late] == ["Groceries"]
        early = get_recent_transactions(1, end_date=_seed_d(5))
        assert sorted(r["description"] for r in early) == ["Lunch", "Monthly bus pass"]

    def test_recent_transactions_respects_limit_with_dates(self, app):
        rows = get_recent_transactions(1, limit=2, start_date=_seed_d(1), end_date=_seed_d(24))
        assert len(rows) == 2

    def test_recent_transactions_no_dates_unchanged(self, app):
        assert len(get_recent_transactions(1)) == 8

    def test_category_breakdown_filtered_pct_sums_to_100(self, app):
        cats = get_category_breakdown(1, start_date=_seed_d(10), end_date=_seed_d(20))
        assert len(cats) == 3
        assert sum(c["pct"] for c in cats) == 100
        assert {c["name"] for c in cats} == {"Entertainment", "Shopping", "Other"}

    def test_category_breakdown_no_dates_seven_categories(self, app):
        cats = get_category_breakdown(1)
        assert len(cats) == 7
        assert sum(c["pct"] for c in cats) == 100

    def test_category_breakdown_empty_range(self, app):
        assert get_category_breakdown(1, start_date="1999-01-01", end_date="1999-01-02") == []

    def test_helpers_never_leak_other_users(self, app):
        _, uid = _second_user_client(app)
        _add_expense(uid, 999.0, "Other", _seed_d(12), "Other user secret")
        rows = get_recent_transactions(1, start_date=_seed_d(1), end_date=_seed_d(28))
        assert "Other user secret" not in [r["description"] for r in rows]
        assert get_summary_stats(1, start_date=_seed_d(1), end_date=_seed_d(28))["total_spent"] == pytest.approx(330.78)
        mine = get_summary_stats(uid, start_date=_seed_d(1), end_date=_seed_d(28))
        assert mine["transaction_count"] == 1

    @pytest.mark.parametrize(
        "payload",
        ["2026-01-01' OR '1'='1", "'; DROP TABLE expenses;--"],
    )
    def test_helpers_treat_dates_as_data_not_sql(self, app, payload):
        get_summary_stats(1, start_date=payload)
        get_recent_transactions(1, end_date=payload)
        get_category_breakdown(1, start_date=payload, end_date=payload)
        assert len(_db_snapshot()) == 8, "expenses table must be intact"


# --------------------------------------------------------------------- #
# Route: auth guard                                                     #
# --------------------------------------------------------------------- #

class TestAuthGuard:
    @pytest.mark.parametrize(
        "qs",
        ["", f"?start={SEED_MONTH}-10", "?range=this-month", "?start=bad", "?start=2026-12-31&end=2026-01-01"],
    )
    def test_signed_out_redirects_to_login(self, client, qs):
        resp = client.get("/profile" + qs)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_signed_out_does_not_leak_data(self, client):
        resp = client.get("/profile?range=all", follow_redirects=True)
        body = _text(resp)
        for desc in ALL_DESCRIPTIONS:
            assert desc not in body, f"{desc} leaked to anonymous user"


# --------------------------------------------------------------------- #
# Route: no params / regression                                         #
# --------------------------------------------------------------------- #

class TestNoParams:
    def test_no_params_shows_all_expenses(self, demo_client):
        resp = demo_client.get("/profile")
        body = _text(resp)
        assert resp.status_code == 200
        assert "₹330.78" in body
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, f"{desc} missing from unfiltered profile"

    def test_no_params_caption_is_all_time(self, demo_client):
        assert "Showing all time" in _text(demo_client.get("/profile"))

    def test_filter_bar_present(self, demo_client):
        body = _text(demo_client.get("/profile"))
        for label in ("This month", "Last month", "Last 3 months", "All time"):
            assert label in body, f"Preset '{label}' missing"
        assert 'type="date"' in body
        assert 'name="start"' in body
        assert 'name="end"' in body
        assert "Apply" in body
        assert "Clear" in body

    def test_filter_form_uses_get(self, demo_client):
        body = _text(demo_client.get("/profile")).lower()
        assert 'method="get"' in body

    def test_filter_bar_precedes_stat_tiles(self, demo_client):
        body = _text(demo_client.get("/profile"))
        assert body.index('name="start"') < body.index("₹330.78")

    def test_all_time_preset_active_by_default(self, demo_client):
        import re
        body = _text(demo_client.get("/profile"))
        assert re.search(r"<a[^>]*is-active[^>]*>\s*All time", body), "All time should be active"


# --------------------------------------------------------------------- #
# Route: custom start/end                                               #
# --------------------------------------------------------------------- #

class TestCustomRange:
    def test_start_and_end(self, demo_client):
        resp = demo_client.get(f"/profile?start={_seed_d(10)}&end={_seed_d(20)}")
        body = _text(resp)
        assert resp.status_code == 200
        assert "₹85.99" in body
        for desc in ("Movie night", "New shoes", "Gift wrap"):
            assert desc in body
        for desc in ("Lunch", "Monthly bus pass", "Electricity bill", "Pharmacy", "Groceries"):
            assert desc not in body, f"{desc} should be filtered out"
        assert "Shopping" in body

    def test_start_only(self, demo_client):
        body = _text(demo_client.get(f"/profile?start={_seed_d(20)}"))
        assert "Groceries" in body
        assert "₹72.30" in body
        for desc in ("Lunch", "New shoes", "Gift wrap"):
            assert desc not in body

    def test_end_only(self, demo_client):
        body = _text(demo_client.get(f"/profile?end={_seed_d(5)}"))
        assert "₹57.50" in body
        assert "Lunch" in body and "Monthly bus pass" in body
        for desc in ("Electricity bill", "Groceries", "New shoes"):
            assert desc not in body

    def test_inclusive_boundaries_in_route(self, demo_client):
        body = _text(demo_client.get(f"/profile?start={_seed_d(12)}&end={_seed_d(12)}"))
        assert "Movie night" in body
        assert "₹15.99" in body
        assert "New shoes" not in body

    def test_inputs_prefilled_with_active_bounds(self, demo_client):
        body = _text(demo_client.get(f"/profile?start={_seed_d(10)}&end={_seed_d(20)}"))
        assert f'value="{_seed_d(10)}"' in body
        assert f'value="{_seed_d(20)}"' in body

    def test_caption_shows_active_period(self, demo_client):
        body = _text(demo_client.get(f"/profile?start={_seed_d(10)}&end={_seed_d(20)}"))
        s = date.fromisoformat(_seed_d(10)).strftime("%d %b %Y")
        e = date.fromisoformat(_seed_d(20)).strftime("%d %b %Y")
        assert f"Showing {s} – {e}" in body

    def test_blank_inputs_from_form_submit_show_all(self, demo_client):
        resp = demo_client.get("/profile?start=&end=")
        body = _text(resp)
        assert resp.status_code == 200
        for desc in ALL_DESCRIPTIONS:
            assert desc in body

    def test_filtering_does_not_change_data(self, demo_client):
        before = _db_snapshot()
        for qs in (
            f"?start={_seed_d(10)}&end={_seed_d(20)}",
            "?range=last-month",
            "?start=bad",
            "?start=2026-12-31&end=2026-01-01",
        ):
            demo_client.get("/profile" + qs)
        assert _db_snapshot() == before, "Filtering must be read-only"


# --------------------------------------------------------------------- #
# Route: presets                                                        #
# --------------------------------------------------------------------- #

class TestPresets:
    def test_this_month_includes_seed_rows_up_to_today(self, demo_client):
        import re
        rows, total = _expected_this_month()
        resp = demo_client.get("/profile?range=this-month")
        body = _text(resp)
        assert resp.status_code == 200
        assert f"₹{total:,.2f}" in body
        for _, _, _, desc in rows:
            assert desc in body
        for _, _, _, desc in [s for s in SEED if s[0] > TODAY.day]:
            assert desc not in body, f"{desc} is after today, must be excluded"
        assert re.search(r"<a[^>]*is-active[^>]*>\s*This month", body)

    def test_this_month_caption(self, demo_client):
        body = _text(demo_client.get("/profile?range=this-month"))
        first = TODAY.replace(day=1).strftime("%d %b %Y")
        assert f"Showing {first} – {TODAY.strftime('%d %b %Y')}" in body

    def test_this_month_prefills_inputs(self, demo_client):
        body = _text(demo_client.get("/profile?range=this-month"))
        assert f'value="{TODAY.replace(day=1).isoformat()}"' in body
        assert f'value="{TODAY.isoformat()}"' in body

    def test_last_month_empty_state(self, demo_client):
        import re
        resp = demo_client.get("/profile?range=last-month")
        body = _text(resp)
        assert resp.status_code == 200
        assert "₹0.00" in body
        assert "—" in body, "Top category should be an em dash"
        assert "No expenses in this period" in body
        assert "No expenses yet" not in body
        for desc in ALL_DESCRIPTIONS:
            assert desc not in body
        assert re.search(r"<a[^>]*is-active[^>]*>\s*Last month", body)

    def test_last_month_includes_only_last_month_rows(self, demo_client):
        prev_last = TODAY.replace(day=1) - timedelta(days=1)
        first_prev = prev_last.replace(day=1)
        _add_expense(1, 33.33, "Food", first_prev.isoformat(), "PrevFirst")
        _add_expense(1, 44.44, "Food", prev_last.isoformat(), "PrevLast")
        _add_expense(1, 55.55, "Food", (first_prev - timedelta(days=1)).isoformat(), "TwoMonthsAgo")
        body = _text(demo_client.get("/profile?range=last-month"))
        assert "PrevFirst" in body and "PrevLast" in body
        assert "TwoMonthsAgo" not in body
        assert "Lunch" not in body
        assert "₹77.77" in body

    def test_last_3_months_window(self, demo_client):
        start = _month_shift(TODAY, 2)
        before = _month_shift(TODAY, 3) + timedelta(days=14)
        _add_expense(1, 1.11, "Food", (start + timedelta(days=14)).isoformat(), "InWindow")
        _add_expense(1, 2.22, "Food", start.isoformat(), "WindowFirstDay")
        _add_expense(1, 3.33, "Food", before.isoformat(), "TooOld")
        body = _text(demo_client.get("/profile?range=last-3-months"))
        assert "InWindow" in body
        assert "WindowFirstDay" in body
        assert "TooOld" not in body
        assert "Lunch" in body, "Seed month rows on/before today are in range"

    def test_last_3_months_excludes_future_dates(self, demo_client):
        _add_expense(1, 5.0, "Food", (TODAY + timedelta(days=5)).isoformat(), "FutureRow")
        body = _text(demo_client.get("/profile?range=last-3-months"))
        assert "FutureRow" not in body

    def test_all_preset_shows_everything(self, demo_client):
        _add_expense(1, 1.0, "Food", "2001-01-01", "AncientRow")
        body = _text(demo_client.get("/profile?range=all"))
        assert "AncientRow" in body
        for desc in ALL_DESCRIPTIONS:
            assert desc in body
        assert "Showing all time" in body

    def test_range_takes_priority_over_start_end(self, demo_client):
        resp = demo_client.get(f"/profile?range=last-month&start={_seed_d(10)}&end={_seed_d(20)}")
        body = _text(resp)
        assert resp.status_code == 200
        assert "Movie night" not in body, "range must override start/end"
        assert "No expenses in this period" in body

    def test_range_all_overrides_start_end(self, demo_client):
        body = _text(demo_client.get(f"/profile?range=all&start={_seed_d(20)}"))
        assert "Lunch" in body and "Groceries" in body

    def test_preset_links_target_profile_with_range(self, demo_client):
        body = _text(demo_client.get("/profile"))
        for key in ("this-month", "last-month", "last-3-months", "all"):
            assert f"range={key}" in body, f"Missing link for preset {key}"

    def test_only_one_preset_active(self, demo_client):
        body = _text(demo_client.get("/profile?range=last-month"))
        # CSS is not inlined, so the class should only be on the active link.
        assert body.count("is-active") == 1


# --------------------------------------------------------------------- #
# Route: validation                                                     #
# --------------------------------------------------------------------- #

class TestValidation:
    INVALID_MSG = "Invalid date — showing all expenses."
    ORDER_MSG = "Start date must be before end date."

    @pytest.mark.parametrize(
        "qs",
        [
            "?start=not-a-date",
            "?end=not-a-date",
            "?start=2026-02-30",
            "?start=2026-13-01",
            "?start=01/02/2026",
            f"?start={SEED_MONTH}-10&end=garbage",
            "?start=2026-01-01'%20OR%20'1'='1",
            "?start=';%20DROP%20TABLE%20expenses;--",
            "?start=" + "9" * 500,
        ],
    )
    def test_invalid_date_flashes_error_and_shows_all(self, demo_client, qs):
        resp = demo_client.get("/profile" + qs)
        body = _text(resp)
        assert resp.status_code == 200, "Must render, not redirect"
        assert self.INVALID_MSG in body
        for desc in ALL_DESCRIPTIONS:
            assert desc in body, f"{desc} should be shown unfiltered"
        assert "₹330.78" in body
        assert len(_db_snapshot()) == 8

    def test_start_after_end_flashes_error_and_shows_all(self, demo_client):
        resp = demo_client.get("/profile?start=2026-12-31&end=2026-01-01")
        body = _text(resp)
        assert resp.status_code == 200
        assert self.ORDER_MSG in body
        for desc in ALL_DESCRIPTIONS:
            assert desc in body
        assert self.INVALID_MSG not in body

    def test_start_equal_end_is_valid(self, demo_client):
        body = _text(demo_client.get(f"/profile?start={_seed_d(12)}&end={_seed_d(12)}"))
        assert self.ORDER_MSG not in body
        assert self.INVALID_MSG not in body

    @pytest.mark.parametrize("qs", ["?range=bogus", "?range=", "?range=THIS-MONTH", "?range=all;--"])
    def test_unknown_range_ignored_no_error(self, demo_client, qs):
        resp = demo_client.get("/profile" + qs)
        body = _text(resp)
        assert resp.status_code == 200
        assert self.INVALID_MSG not in body
        assert self.ORDER_MSG not in body
        for desc in ALL_DESCRIPTIONS:
            assert desc in body

    def test_unknown_range_with_valid_dates_uses_dates(self, demo_client):
        body = _text(demo_client.get(f"/profile?range=bogus&start={_seed_d(20)}"))
        assert "Groceries" in body
        assert "Lunch" not in body

    def test_error_does_not_persist_to_next_request(self, demo_client):
        demo_client.get("/profile?start=bad")
        body = _text(demo_client.get("/profile"))
        assert self.INVALID_MSG not in body


# --------------------------------------------------------------------- #
# Route: empty states                                                   #
# --------------------------------------------------------------------- #

class TestEmptyStates:
    def test_user_with_no_expenses_sees_no_expenses_yet(self, app):
        c, _ = _second_user_client(app)
        body = _text(c.get("/profile"))
        assert "No expenses yet" in body
        assert "No expenses in this period" not in body

    def test_user_with_no_expenses_and_filter_sees_no_expenses_yet(self, app):
        c, _ = _second_user_client(app)
        body = _text(c.get("/profile?range=this-month"))
        assert "No expenses yet" in body
        assert "No expenses in this period" not in body

    def test_user_with_expenses_but_none_in_range(self, demo_client):
        body = _text(demo_client.get("/profile?start=1999-01-01&end=1999-12-31"))
        assert "No expenses in this period" in body
        assert "No expenses yet" not in body

    def test_empty_period_has_clear_link_to_unfiltered_profile(self, demo_client):
        body = _text(demo_client.get("/profile?start=1999-01-01&end=1999-12-31"))
        assert 'href="/profile"' in body, "Clear-filter link should point to plain /profile"

    def test_empty_period_zero_totals_and_dash_top_category(self, demo_client):
        body = _text(demo_client.get("/profile?start=1999-01-01&end=1999-12-31"))
        assert "₹0.00" in body
        assert "—" in body


# --------------------------------------------------------------------- #
# Route: user isolation                                                 #
# --------------------------------------------------------------------- #

class TestIsolation:
    @pytest.mark.parametrize(
        "qs",
        [
            "",
            "?range=all",
            "?range=this-month",
            "?range=last-3-months",
            f"?start={SEED_MONTH}-01&end={SEED_MONTH}-28",
            f"?start={SEED_MONTH}-01",
            f"?end={SEED_MONTH}-28",
        ],
    )
    def test_second_user_never_sees_demo_expenses(self, app, qs):
        c, _ = _second_user_client(app)
        body = _text(c.get("/profile" + qs))
        for desc in ALL_DESCRIPTIONS:
            assert desc not in body, f"Demo expense '{desc}' leaked with filter {qs!r}"
        assert "₹330.78" not in body

    def test_second_user_sees_only_own_filtered_expenses(self, app):
        c, uid = _second_user_client(app)
        _add_expense(uid, 7.77, "Food", _seed_d(12), "OtherLatte")
        _add_expense(uid, 8.88, "Food", _seed_d(2), "OtherEarly")
        body = _text(c.get(f"/profile?start={_seed_d(10)}&end={_seed_d(20)}"))
        assert "OtherLatte" in body
        assert "₹7.77" in body
        assert "OtherEarly" not in body
        assert "Movie night" not in body

    def test_user_id_query_param_is_ignored(self, app):
        c, _ = _second_user_client(app)
        body = _text(c.get("/profile?user_id=1&range=all"))
        for desc in ALL_DESCRIPTIONS:
            assert desc not in body

    def test_demo_does_not_see_other_users_expenses(self, demo_client, app):
        _, uid = _second_user_client(app, email="third@example.com")
        _add_expense(uid, 500.0, "Food", _seed_d(12), "ThirdUserSecret")
        body = _text(demo_client.get(f"/profile?start={_seed_d(1)}&end={_seed_d(28)}"))
        assert "ThirdUserSecret" not in body


# --------------------------------------------------------------------------- #
# Preset date maths (fixed "today" values, including year rollover)           #
# --------------------------------------------------------------------------- #

class TestPresetBounds:
    @pytest.mark.parametrize(
        "key, today, expected",
        [
            ("this-month", date(2026, 10, 24), (date(2026, 10, 1), date(2026, 10, 24))),
            ("last-month", date(2026, 10, 24), (date(2026, 9, 1), date(2026, 9, 30))),
            ("last-month", date(2026, 1, 15), (date(2025, 12, 1), date(2025, 12, 31))),
            ("last-month", date(2024, 3, 31), (date(2024, 2, 1), date(2024, 2, 29))),
            ("last-3-months", date(2026, 10, 24), (date(2026, 8, 1), date(2026, 10, 24))),
            ("last-3-months", date(2026, 1, 15), (date(2025, 11, 1), date(2026, 1, 15))),
            ("last-3-months", date(2026, 2, 28), (date(2025, 12, 1), date(2026, 2, 28))),
            ("all", date(2026, 10, 24), (None, None)),
            ("bogus", date(2026, 10, 24), (None, None)),
        ],
    )
    def test_preset_bounds(self, key, today, expected):
        assert _preset_bounds(key, today) == expected
