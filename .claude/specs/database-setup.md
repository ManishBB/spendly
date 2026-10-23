# Spec Document: Spendly SQLite Database Foundation

## 1. Overview

Replace the stub implementation in `database/db.py` with a working SQLite implementation.

This step establishes the **data layer foundation** for the Spendly application. All future features, including authentication, user profiles, and expense tracking, depend on this implementation.

## 2. Dependencies

This is the first implementation step and has no dependencies on other features.

## 3. Routes

- No new routes are required.
- Existing placeholder routes in `app.py` must remain unchanged.

## 4. Database Schema

### A. `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | Primary key, autoincrement |
| `name` | TEXT | Not null |
| `email` | TEXT | Unique, not null |
| `password_hash` | TEXT | Not null |
| `created_at` | TEXT | Default `datetime('now')` |

### B. `expenses`

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | Primary key, autoincrement |
| `user_id` | INTEGER | Foreign key referencing `users.id`, not null |
| `amount` | REAL | Not null |
| `category` | TEXT | Not null |
| `date` | TEXT | Not null; `YYYY-MM-DD` format |
| `description` | TEXT | Nullable |
| `created_at` | TEXT | Default `datetime('now')` |

## 5. Functions to Implement (`database/db.py`)

### A. `get_db()`

Implement a function that:

- Opens a connection to `spendly.db` in the project root. Using `expense_tracker.db` is also acceptable if applied consistently.
- Sets `connection.row_factory = sqlite3.Row` for dictionary-like row access.
- Enables foreign key enforcement using `PRAGMA foreign_keys = ON`.
- Returns the active SQLite connection.

### B. `init_db()`

Implement a function that:

- Creates the `users` and `expenses` tables.
- Uses `CREATE TABLE IF NOT EXISTS` for both tables.
- Defines all columns, primary keys, uniqueness constraints, and foreign key relationships according to the schema.
- Is safe to call repeatedly without failing or recreating existing tables.
- Ensures the database schema is ready before the application handles requests.

### C. `seed_db()`

Implement a function that seeds the database with demo data.

#### Duplicate prevention

- Check whether the `users` table already contains at least one record.
- If a user already exists, return early without inserting demo data.
- Ensure repeated calls do not create duplicate seed records.

#### Demo user

Insert one demo user with the following details:

| Field | Value |
|---|---|
| Name | `Demo User` |
| Email | `demo@spendly.com` |
| Password | `demo123` |

Requirements:

- Hash the password using `werkzeug.security.generate_password_hash`.
- Store only the resulting hash in `password_hash`; never store the plaintext password.

#### Sample expenses

Insert exactly **8 sample expenses** linked to the demo user's ID.

Requirements:

- Use multiple expense categories.
- Cover all seven categories listed in Section 10, with at least one expense per category.
- Spread the expense dates across the current month.
- Use valid `YYYY-MM-DD` date strings.
- Include realistic amounts and descriptions where appropriate.

### Transaction safety

- Use parameterized SQL for all data values.
- Use transactions to ensure the demo user and its sample expenses are inserted consistently.
- Commit successful inserts and roll back on failure.
- Close database connections when they are no longer needed.

## 6. Changes to `app.py`

Update `app.py` as follows:

1. Import `get_db`, `init_db`, and `seed_db` from `database.db`.
2. During application startup, enter `app.app_context()`.
3. Call `init_db()` followed by `seed_db()` inside the application context.
4. Ensure database initialization and seeding complete before the application serves requests.
5. Keep all existing placeholder routes unchanged.

## 7. Files to Change

- `database/db.py` — Implement `get_db()`, `init_db()`, and `seed_db()`.
- `app.py` — Add the required imports and startup initialization calls.

## 8. Files to Create

None. Use the existing project structure.

## 9. Dependencies

No new pip packages are required.

Use:

- `sqlite3` — Python standard library.
- `werkzeug.security.generate_password_hash` — Password hashing; Werkzeug is already installed.

## 10. Fixed Expense Categories

Use exactly these seven category values:

1. `Food`
2. `Transport`
3. `Bills`
4. `Health`
5. `Entertainment`
6. `Shopping`
7. `Other`

Do not introduce alternative category names or variations in capitalization.

## 11. Implementation Rules

- Do not use an ORM such as SQLAlchemy.
- Use parameterized SQL queries exclusively for data values.
- Never interpolate user-provided or variable data into SQL strings.
- Enable `PRAGMA foreign_keys = ON` on every database connection.
- Store `amount` as `REAL`, not `INTEGER`.
- Hash passwords using:

  ```python
  from werkzeug.security import generate_password_hash
  ```

- Prevent duplicate seed data on repeated calls.
- Keep dates consistently formatted as `YYYY-MM-DD`.
- Use appropriate connection and transaction management.
- Do not change existing application routes or introduce unrelated dependencies.

## 12. Expected Behavior

### `get_db()`

- Returns a working SQLite connection.
- Supports dictionary-like row access through `sqlite3.Row`.
- Enforces foreign key constraints.

### `init_db()`

- Creates the database file when it does not exist.
- Creates both tables with the correct schema and constraints.
- Can run repeatedly without failing.

### `seed_db()`

- Inserts the demo user and sample expenses when the database is empty.
- Stores a hashed password for the demo user.
- Inserts eight sample expenses covering all seven categories.
- Avoids duplicate seed records on subsequent calls.

### Database constraints

- Duplicate user emails are rejected by the unique constraint.
- Expenses referencing nonexistent users are rejected by the foreign key constraint.
- Invalid SQL statements or database operations raise clear errors suitable for debugging.

## 13. Error Handling Expectations

- **Duplicate email:** Inserting a user with an existing email must raise an SQLite integrity error.
- **Invalid foreign key:** Inserting an expense with an invalid `user_id` must raise an SQLite integrity error.
- **Invalid SQL:** Database errors must be surfaced clearly rather than silently ignored.
- **Seed failures:** Failed seed transactions must be rolled back to avoid partially inserted demo data.
- **Connection cleanup:** Connections must be closed appropriately, including when an operation fails.

## 14. Definition of Done

- [ ] Database file is created on application startup.
- [ ] Both tables exist with the correct schema and constraints.
- [ ] Demo user exists with a securely hashed password.
- [ ] Eight sample expenses exist across all seven categories.
- [ ] Sample expense dates are spread across the current month.
- [ ] Repeated startup does not duplicate seed data.
- [ ] Application starts without errors.
- [ ] Foreign key enforcement works on every connection.
- [ ] Duplicate email insertion is rejected.
- [ ] Expenses with invalid user IDs are rejected.
- [ ] All SQL data values use parameterized queries.
- [ ] Database transactions roll back correctly on failure.
- [ ] Existing routes in `app.py` remain unchanged.
