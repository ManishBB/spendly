# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** is a Flask-based expense tracking web application. This appears to be a learning/tutorial project with placeholder routes and database stubs that students will implement step-by-step.

## Technology Stack

- **Backend**: Flask 3.1.3 with Werkzeug 3.1.6
- **Database**: SQLite (via `database/db.py` module)
- **Frontend**: HTML templates (Jinja2), custom CSS with CSS variables, minimal JavaScript
- **Testing**: pytest 8.3.5 with pytest-flask 1.3.0

## Development Commands

### Running the Application
```bash
python app.py
```
The app runs on port 5001 with debug mode enabled by default.

### Running Tests
```bash
pytest
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Project Structure

### Application Entry Point
- `app.py` - Main Flask application with route definitions
  - Runs on port 5001
  - Currently has basic routes implemented (landing, register, login)
  - Contains placeholder routes for future implementation (logout, profile, expense CRUD operations)

### Database Layer
- `database/db.py` - Database connection and initialization module
  - Should contain `get_db()` - returns SQLite connection with row_factory and foreign keys enabled
  - Should contain `init_db()` - creates tables using CREATE TABLE IF NOT EXISTS
  - Should contain `seed_db()` - inserts sample data for development
  - Currently contains only placeholder comments; implementation is a pending task

### Frontend

**Templates** (`templates/`):
- `base.html` - Base template with navbar, footer, and common structure
  - Uses Jinja2 template inheritance with `{% block content %}` and `{% block scripts %}`
  - Navbar includes links to landing, login, register
  - Loads Google Fonts (DM Serif Display, DM Sans)
  - Brand name: "Spendly" with diamond icon (◈)

**Static Assets** (`static/`):
- `css/style.css` - Custom CSS with design system
  - Uses CSS custom properties (variables) defined in `:root`
  - Color palette: ink/paper metaphor with accent colors
  - Typography: DM Serif Display for headings, DM Sans for body
  - Components: navbar, hero, features, auth forms, footer
  - Responsive design with breakpoints at 900px and 600px

- `js/main.js` - Client-side JavaScript (currently empty placeholder)

## Key Architecture Patterns

### Route Organization
Routes in `app.py` are organized into two sections:
1. **Implemented routes** - Landing page and auth pages (lines 10-22)
2. **Placeholder routes** - Features to be implemented in steps 3-9 (lines 29-51)

### Template Inheritance
All pages extend `base.html` using Jinja2's template inheritance:
```html
{% extends "base.html" %}
{% block content %}...{% endblock %}
```

### Design System
The CSS uses a comprehensive design token system:
- Color tokens: `--ink-*` (text), `--paper-*` (backgrounds), `--accent-*` (brand colors)
- Typography tokens: `--font-display`, `--font-body`
- Spacing/sizing tokens: `--auth-width`, `--max-width`, `--radius-*`

### Database Pattern (To Be Implemented)
The expected pattern based on comments:
- Connection management via `get_db()` with proper row factory
- Schema initialization via `init_db()` with IF NOT EXISTS checks
- Development data seeding via `seed_db()`

## Planned Features (Not Yet Implemented)

Based on placeholder routes in `app.py`:
- Step 3: User logout functionality
- Step 4: User profile page
- Step 7: Add expense functionality
- Step 8: Edit expense functionality (route: `/expenses/<int:id>/edit`)
- Step 9: Delete expense functionality (route: `/expenses/<int:id>/delete`)

## Testing

The project includes pytest and pytest-flask. When writing tests:
- Use pytest fixtures for Flask app and database setup
- Test database operations in isolation
- Test route handlers with the Flask test client
- Follow pytest naming conventions (`test_*.py` files, `test_*` functions)