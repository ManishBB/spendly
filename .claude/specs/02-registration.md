# Spec: Registration

## Overview
This step makes the existing sign-up page work. Right now `GET /register` only renders `templates/register.html`, and the form's `POST /register` has nowhere to go. This step adds a POST handler that validates the submitted name, email and password, hashes the password with werkzeug, and inserts a new row into the `users` table. If the input is invalid, the form is shown again with a clear error. If it succeeds, the user is redirected to the sign-in page with a success message. Registration is the first feature that writes user-supplied data to the database, so the login (Step 3), profile (Step 4) and expense steps (7–9) all need it.

## Depends on
- **Step 1 — Database setup:** `get_db()`, `init_db()` and the `users` table (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`) in `database/db.py`.

## Routes
- `GET /register` — render the registration form (already exists; keep its behaviour) — public
- `POST /register` — validate the form, create the user, redirect to `/login` on success or re-render `register.html` with an error on failure — public

The existing `register()` view handles both methods via `methods=["GET", "POST"]`. No separate route function.

## Database changes
No database changes. The `users` table in `database/db.py` already has every column needed, and its `UNIQUE` constraint on `email` enforces no duplicates.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — after a failed submission, keep the submitted `name` and `email` in the inputs (`value="{{ name or '' }}"` and `value="{{ email or '' }}"`). Never refill the password. Add `minlength="8"` to the password input. The existing `{% if error %}` block stays as the error display.
  - `templates/login.html` — show flashed messages above the form (for example "Account created — please sign in.") in a new `.auth-success` block, using `get_flashed_messages(with_categories=true)`.

## Files to change
- `app.py`
  - import `request`, `redirect`, `url_for`, `flash` from `flask`
  - set `app.secret_key` (read from the `SECRET_KEY` environment variable, falling back to a dev-only default) so `flash` works
  - change `register()` to accept `GET` and `POST` and implement the POST logic
- `database/db.py` — add `create_user(name, email, password)`, which hashes the password, inserts the user with a parameterised query, and returns the new user id. It raises `sqlite3.IntegrityError` on a duplicate email. Also add `get_user_by_email(email)`, which returns a `sqlite3.Row` or `None`.
- `templates/register.html` — see Templates
- `templates/login.html` — see Templates
- `static/css/style.css` — add an `.auth-success` class that mirrors `.auth-error`, using `--accent-light` / `--accent`. Also replace the hardcoded `#f5c6c2` border in `.auth-error` with a CSS variable (e.g. a new `--danger-border` token in `:root`).

## Files to create
- `tests/test_registration.py` — pytest tests for the registration route (see Definition of done)
- `tests/conftest.py` — fixtures for a Flask test client backed by a temporary SQLite database (patch `database.db.DB_PATH` to a `tmp_path` file)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting or f-strings to build SQL
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log the plaintext password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validation runs on the server, whatever HTML attributes the form has:
  - `name`, `email`, `password` are all required; strip surrounding whitespace from `name` and `email`
  - lowercase `email` before checking and storing it
  - `email` must look like an email (contains a single `@` with text on both sides and a `.` in the domain)
  - `password` must be at least 8 characters
- Detect a duplicate email by catching `sqlite3.IntegrityError` from the insert, not only by checking first, so a race between two sign-ups can't create two accounts
- On a validation error, re-render `register.html` with HTTP status 400 and a specific `error` message. Pass back `name` and `email`, never `password`
- On success, `flash` a success message and `redirect(url_for("login"))` (Post/Redirect/Get)
- Always close database connections (`try`/`finally`), as the existing `db.py` functions do
- Do not start a session or log the user in — login is Step 3
- Leave all placeholder routes in `app.py` unchanged

## Definition of done
- [ ] `python app.py` starts without errors and `GET /register` renders the form
- [ ] Submitting valid details (e.g. `Test User`, `test@example.com`, `password123`) redirects to `/login`, and the page shows a success message
- [ ] A new row exists in `users` with that name and lowercased email, and `password_hash` is a werkzeug hash (not the plaintext password)
- [ ] Registering again with the same email (in any letter case, e.g. `TEST@example.com`) re-shows the form with an "email already registered" error and creates no new row
- [ ] Registering with `demo@spendly.com` (the seeded user) is rejected as a duplicate
- [ ] Submitting a password shorter than 8 characters shows an error and creates no user
- [ ] Submitting a blank name, a blank email, or a malformed email (e.g. `notanemail`) shows an error and creates no user
- [ ] After any failed submission, the name and email fields are still filled in and the password field is empty
- [ ] Error responses return HTTP 400; a successful registration returns a 302 redirect
- [ ] The success and error message boxes use only CSS variables (no hex values in the new or changed rules)
- [ ] `pytest` passes, with tests covering: successful registration, duplicate email, short password, missing fields, invalid email
