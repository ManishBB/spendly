# Spec: Date Filter for Profile Page

## Overview
Step 6 lets the user limit the profile page to a date range. Right now `/profile` always shows every expense the user has ever logged, so the summary tiles, category breakdown, and recent expenses can't answer questions like "what did I spend last month?". This step adds a small filter bar above the stat tiles. It has preset ranges (This month, Last month, Last 3 months, All time) and a custom start/end date form. The filter is passed as query-string parameters on the existing `GET /profile` route, and the three query helpers in `database/queries.py` accept an optional date range so every data section on the page reflects the same period. The page is still read-only, and it gives the expense CRUD steps (7–9) a more useful page to land on.

## Depends on
- **Step 1 — Database setup:** the `expenses` table, with `date` stored as ISO `YYYY-MM-DD` text
- **Step 3 — Login and logout:** `session["user_id"]`
- **Step 4 — Profile page:** `templates/profile.html` and the profile CSS section
- **Step 5 — Profile backend routes:** `database/queries.py` helpers (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown`)

## Routes
No new routes. The existing `GET /profile` route (logged-in) is modified to read optional query parameters:
- `start` — inclusive start date, `YYYY-MM-DD`
- `end` — inclusive end date, `YYYY-MM-DD`
- `range` — optional preset key: `this-month`, `last-month`, `last-3-months`, `all`

Behaviour:
- No parameters means all time, which matches the current behaviour.
- A `range` preset is resolved server-side into `start`/`end` from `date.today()`. If `range` is present, it takes priority over `start`/`end`.
  - `this-month`: the 1st of the current month to today
  - `last-month`: the 1st to the last day of the previous month
  - `last-3-months`: the 1st of the month two months ago to today
  - `all`: no bounds
- Only one bound may be set. `start` alone means "from start onward", and `end` alone means "up to end".
- An invalid date string (one that doesn't parse with `date.fromisoformat`) flashes "Invalid date — showing all expenses." (`error`). The page then renders unfiltered with status 200. It doesn't redirect.
- If `start` is after `end`, the page flashes "Start date must be before end date." (`error`) and renders unfiltered.
- An unknown `range` value is ignored, which means all time.

## Database changes
No database changes. `expenses.date` is already ISO text, so string comparison (`date >= ?` / `date <= ?`) is correct.

Modify these helpers in `database/queries.py` so each one takes optional `start_date=None, end_date=None` keyword arguments (ISO strings) and adds `AND date >= ?` / `AND date <= ?` only when the argument is set:
- `get_summary_stats(user_id, start_date=None, end_date=None)`
- `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`
- `get_category_breakdown(user_id, start_date=None, end_date=None)`

Build the WHERE clause from a fixed list of SQL fragments and a matching params list. A shared private helper such as `_date_clause(start_date, end_date)` that returns `(sql_fragment, params)` is fine. Existing call sites with no dates must behave exactly as before.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter bar between the profile header and the stat tiles:
    - Preset links (`url_for('profile', range=...)`) for This month, Last month, Last 3 months, and All time. Mark the active one with an `is-active` class.
    - A `GET` form with two `<input type="date">` fields (`name="start"`, `name="end"`), pre-filled with the active bounds, plus an "Apply" button and a "Clear" link to `url_for('profile')`.
  - Show a caption for the active period above the tiles, e.g. "Showing 01 Oct 2026 – 24 Oct 2026" or "Showing all time".
  - Split the empty state into two cases:
    - The user has no expenses at all: keep the existing "No expenses yet" panel.
    - The user has expenses but none in the selected range: show "No expenses in this period" with a link to clear the filter.

## Files to change
- `app.py` — parse and validate `start`/`end`/`range` in `profile()`, resolve presets, and pass the bounds through `_summary_stats`, `_transaction_history` and `_category_breakdown` to the query helpers. Pass `start`, `end`, `active_range` and `period_label` to the template.
- `database/queries.py` — optional date-range arguments on the three helpers
- `templates/profile.html` — filter bar, period caption, and the filtered empty state
- `static/css/style.css` — styles for the filter bar (`.profile-filter`, `.filter-presets`, `.filter-preset`, `.filter-preset.is-active`, `.filter-form`, `.filter-caption`), with responsive rules added to the existing 600px breakpoint so the form stacks vertically

## Files to create
- `tests/test_date_filter.py` — unit tests for the query helpers with date bounds, and route tests for `/profile` with each parameter combination

## New dependencies
No new dependencies. Use `datetime.date` from the standard library for parsing and preset maths.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only. Date values are always bound with `?` and never formatted into SQL.
- Passwords hashed with werkzeug (this step doesn't touch passwords)
- Use CSS variables. Never hardcode hex values.
- All templates extend `base.html`
- No inline styles and no `|safe`
- Every query still filters by `user_id` from the session, never from request arguments
- Validate dates with `date.fromisoformat`. Never pass a raw query-string value to SQL without parsing it first.
- The filter uses `GET` only, so filtered views can be bookmarked and shared
- No JavaScript is required. The filter must work with JS disabled.
- Amounts keep the `₹1,234.50` format
- `pct` values in the category breakdown must still sum to 100 for any non-empty filtered range
- The "Top category" tile shows "—" when the filtered range is empty
- Don't link to the placeholder expense routes

## Definition of done
Seed dates are relative to the month the database was seeded. "Seed month" below means that month, with expenses on days 1, 3, 6, 9, 12, 15, 19 and 24 totalling ₹330.78.

- [ ] Visiting `/profile` with no parameters as `demo@spendly.com` still shows ₹330.78, 8 expenses, and 7 categories. Nothing has regressed.
- [ ] A filter bar with This month / Last month / Last 3 months / All time links and start/end date inputs appears above the stat tiles
- [ ] `/profile?start=<seed-month>-10&end=<seed-month>-20` shows ₹85.99, 3 expenses (Movie night, New shoes, Gift wrap), 3 categories with percentages summing to 100, and "Top category" Shopping
- [ ] `/profile?start=<seed-month>-20` shows only Groceries (₹72.30, 1 expense)
- [ ] `/profile?end=<seed-month>-05` shows only Lunch and Monthly bus pass (₹57.50, 2 expenses)
- [ ] When the seed month is the current month, clicking "This month" shows all 8 seed expenses and highlights "This month" as active
- [ ] Clicking "Last month" (with no expenses that month) shows ₹0.00, 0 expenses, "—" as the top category, and the "No expenses in this period" message with a clear-filter link, not the "No expenses yet" panel
- [ ] The date inputs are pre-filled with the active start/end after applying a filter, and the caption shows the active period
- [ ] `/profile?start=not-a-date` returns 200, flashes "Invalid date — showing all expenses.", and shows all 8 expenses
- [ ] `/profile?start=2026-12-31&end=2026-01-01` returns 200, flashes "Start date must be before end date.", and shows all 8 expenses
- [ ] `/profile?range=bogus` shows all time with no error
- [ ] A second user applying any filter never sees the demo user's expenses
- [ ] Signed out, `/profile?start=...` still redirects to `/login`
- [ ] The filter bar stacks vertically with no horizontal scroll below 600px
- [ ] No new CSS rules contain hex values
- [ ] `pytest` passes, including the existing `tests/test_profile.py` and `tests/test_backend_connection.py` and the new `tests/test_date_filter.py`
