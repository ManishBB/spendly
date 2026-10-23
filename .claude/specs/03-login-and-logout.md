# Spec: Login and Logout

## Overview
This step makes the sign-in page work and replaces the logout placeholder. Right now `GET /login` only renders `templates/login.html`, the form's `POST /login` has nowhere to go, and `/logout` returns placeholder text. This step adds a POST handler that looks up the user by email, checks the password against the stored werkzeug hash, and stores the user's id and name in Flask's signed `session` cookie. `/logout` clears the session. The navbar changes with the login state: signed-out visitors see "Sign in" / "Get started", and signed-in users see their name and "Sign out". Registration (Step 2) can create accounts, but nobody can use them yet. Login is the base for every later step that is tied to a user: profile (Step 4) and the expense pages (Steps 7–9).

## Depends on
- **Step 1 — Database setup:** `get_db()`, the `users` table, and the seeded demo user (`demo@spendly.com` / `demo123`).
- **Step 2 — Registration:** `get_user_by_email(email)` in `database/db.py`, `app.secret_key` and flash support in `app.py`, the flash message block in `templates/login.html`, and the `.auth-success` / `.auth-error` styles.

## Routes
- `GET /login` — render the sign-in form. If the user is already signed in, redirect to `/profile` — public
- `POST /login` — check the credentials. On success, start a session and redirect to `/profile`. On failure, re-render `login.html` with an error — public
- `GET /logout` — clear the session, flash "You have been signed out.", and redirect to `/login` — public (works even if not signed in)

The existing `login()` view takes both methods via `methods=["GET", "POST"]`. The existing `logout()` placeholder is replaced, and its URL stays the same.

Also change `GET /register`: if the user is already signed in, redirect to `/profile`.

## Database changes
No database changes. The `users` table already has `email` and `password_hash`, and `get_user_by_email()` already exists.

## Templates
- **Create:** none
- **Modify:**
  - `templates/base.html` — make the navbar depend on the session. If `session.get("user_id")` is set, show the user's name (`session["user_name"]`) and a "Sign out" link to `url_for('logout')`. Otherwise keep the current "Sign in" and "Get started" links.
  - `templates/login.html` — after a failed login, keep the submitted email in the input (`value="{{ email or '' }}"`). Never refill the password. The existing flash block and `{% if error %}` block stay as they are.

## Files to change
- `app.py`
  - import `session` from `flask`, and `check_password_hash` from `werkzeug.security`
  - change `login()` to take `GET` and `POST` and implement the POST logic
  - replace the `logout()` placeholder with the real implementation
  - add the already-signed-in redirect to `register()` (GET and POST) and to `login()`
- `templates/base.html` — see Templates
- `templates/login.html` — see Templates
- `static/css/style.css` — add styles for the navbar user name (e.g. `.nav-user`) using existing tokens only. Make sure "Sign out" stays visible on small screens (the 600px breakpoint currently hides `.nav-links a:not(.nav-cta)`).

## Files to create
- `tests/test_auth.py` — pytest tests for login and logout (see Definition of done). Reuse the `app` fixture in `tests/conftest.py` and use `app.test_client()`.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only. Never build SQL with string formatting or f-strings
- Passwords hashed with werkzeug: check them with `check_password_hash(user["password_hash"], password)`. Never compare plaintext, and never log or store the submitted password
- Use CSS variables. Never hardcode hex values
- All templates extend `base.html`
- Strip surrounding whitespace from the email and lowercase it before the lookup, to match how Step 2 stores emails
- Do not apply the 8-character password rule at login. The seeded demo password `demo123` is 7 characters and must still work
- If the email or password is blank, re-render with the error "Email and password are required." and HTTP 400
- If the email is unknown or the password is wrong, show the same message: "Invalid email or password." Use HTTP 401. Never reveal which of the two was wrong
- On success, call `session.clear()` first, then set `session["user_id"]` and `session["user_name"]`. Store nothing else in the session
- On success, `redirect(url_for("profile"))` (Post/Redirect/Get). Do not handle a `next` parameter in this step, to avoid open-redirect bugs
- Logout calls `session.clear()`, flashes a `success` message, and redirects to `url_for("login")`
- Pass the submitted `email` back to the template on failure. Never pass `password` back
- Leave the other placeholder routes (`profile`, `add_expense`, `edit_expense`, `delete_expense`) unchanged. `/profile` will still show placeholder text after login until Step 4
- Do not add a `login_required` decorator yet. Protecting routes belongs to the steps that build those pages

## Definition of done
- [ ] `python app.py` starts without errors, and `GET /login` shows the sign-in form
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/profile`
- [ ] After signing in, the navbar shows "Demo User" and a "Sign out" link instead of "Sign in" / "Get started"
- [ ] Signing in with the email in a different case or with extra spaces (e.g. ` DEMO@Spendly.com `) still works
- [ ] A user created through `/register` can then sign in with their new credentials
- [ ] A wrong password for a real email shows "Invalid email or password." with HTTP 401, and no session is created
- [ ] An unknown email shows the same "Invalid email or password." message with HTTP 401
- [ ] A blank email or blank password shows an error with HTTP 400
- [ ] After a failed login, the email field is still filled in and the password field is empty
- [ ] Clicking "Sign out" redirects to `/login` with a "You have been signed out." message, and the navbar shows "Sign in" / "Get started" again
- [ ] Visiting `/logout` while signed out does not error and redirects to `/login`
- [ ] While signed in, visiting `/login` or `/register` redirects to `/profile`
- [ ] The "Sign out" link stays visible at phone width (below 600px)
- [ ] No new or changed CSS rules contain hex values
- [ ] `pytest` passes, including the existing registration tests and new tests for: successful login, case-insensitive email, wrong password, unknown email, missing fields, session contents after login, logout clearing the session, and the signed-in redirect from `/login`
