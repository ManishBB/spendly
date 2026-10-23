# Spec: Profile Page

## Overview
This step replaces the `/profile` placeholder with the signed-in user's home page. Login (Step 3) and registration already redirect there, but right now it returns placeholder text. The new page shows the user's account details (name, email, member-since date), a spending summary (total spent, this month's total, number of expenses), a breakdown of spending by category, and their most recent expenses. It is the first page that reads the `expenses` table, and it gives the expense pages in Steps 7–9 a place to land.

## Depends on
- **Step 1 — Database setup:** `get_db()`, the `users` and `expenses` tables, and the seeded demo user with 8 expenses.
- **Step 2 — Registration:** flash support and the `.auth-success` / `.auth-error` styles.
- **Step 3 — Login and logout:** `session["user_id"]` / `session["user_name"]`, the session-aware navbar, and the login redirect to `/profile`.

## Routes
- `GET /profile` — show the profile page — logged-in
  - If `session["user_id"]` is not set, flash "Please sign in to view your profile." (`error`) and redirect to `/login`.
  - If the session's user no longer exists, call `session.clear()` and redirect to `/login`.

The existing `profile()` placeholder is replaced, and its URL stays the same.

## Database changes
No database changes. Add these read helpers to `database/db.py`:
- `get_user_by_id(user_id)` — returns `id, name, email, created_at` (never `password_hash`), or `None`
- `get_expense_summary(user_id)` — returns `count`, `total` and `month_total` (current calendar month)
- `get_category_totals(user_id)` — returns `category, total, count` per category, highest total first
- `get_recent_expenses(user_id, limit=10)` — returns the newest expenses first (`date DESC, id DESC`)

## Templates
- **Create:** `templates/profile.html` — header card (avatar initial, name, email, member since), three stat tiles, category bars, recent expenses table, and an empty state when the user has no expenses
- **Modify:** `templates/base.html` — the navbar user name links to `url_for('profile')`

## Files to change
- `app.py` — import the new helpers and replace the `profile()` placeholder. Move it out of the placeholder section.
- `database/db.py` — the new helpers
- `templates/base.html` — see Templates
- `static/css/style.css` — a new "Profile" section, plus responsive rules added to the existing breakpoints

## Files to create
- `templates/profile.html`
- `tests/test_profile.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (this step never touches passwords, and `password_hash` must not reach the template)
- Use CSS variables. Never hardcode hex values
- All templates extend `base.html`
- Every query filters by `user_id` from the session, never from request arguments
- Amounts are shown in rupees with two decimals and thousands separators (`₹1,234.50`)
- No `|safe`. Autoescaping stays on
- No `login_required` decorator yet. The check stays inline in `profile()`
- Do not link to the placeholder expense routes

## Definition of done
- [ ] Signed out, visiting `/profile` redirects to `/login` with "Please sign in to view your profile."
- [ ] A session pointing at a deleted or unknown user is cleared and redirected to `/login`
- [ ] Signing in as `demo@spendly.com` / `demo123` shows "Demo User", the email, and a member-since month
- [ ] The demo user's tiles show a total of ₹330.78 and 8 expenses
- [ ] The category list shows 7 categories, highest total first (Bills before Food)
- [ ] The recent expenses table lists the newest first (Groceries before Lunch)
- [ ] A newly registered user sees ₹0.00 tiles and an empty-state message
- [ ] A second user never sees the demo user's expenses
- [ ] The navbar user name links to `/profile`
- [ ] The page has no horizontal scroll below 600px
- [ ] No new CSS rules contain hex values
- [ ] `pytest` passes, including the new `tests/test_profile.py`
