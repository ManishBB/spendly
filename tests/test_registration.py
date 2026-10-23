import pytest
from werkzeug.security import check_password_hash

from database.db import get_user_by_email


def register(client, name="Test User", email="test@example.com", password="password123"):
    return client.post("/register", data={"name": name, "email": email, "password": password})


def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b'<form method="POST" action="/register">' in response.data


def test_register_success(client):
    response = register(client, email="Test@Example.com")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    user = get_user_by_email("test@example.com")
    assert user is not None
    assert user["name"] == "Test User"
    assert user["password_hash"] != "password123"
    assert check_password_hash(user["password_hash"], "password123")

    login_page = client.get("/login")
    assert "Account created" in login_page.get_data(as_text=True)


def test_register_duplicate_email_case_insensitive(client, user_count):
    register(client, email="test@example.com")
    before = user_count()
    response = register(client, email="TEST@example.com")
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert user_count() == before


def test_register_seeded_demo_email_rejected(client, user_count):
    before = user_count()
    response = register(client, email="demo@spendly.com")
    assert response.status_code == 400
    assert user_count() == before


def test_register_short_password(client, user_count):
    before = user_count()
    response = register(client, password="short")
    assert response.status_code == 400
    assert b"at least 8 characters" in response.data
    assert user_count() == before


@pytest.mark.parametrize(
    "fields",
    [
        {"name": ""},
        {"name": "   "},
        {"email": ""},
        {"password": ""},
    ],
)
def test_register_missing_fields(client, user_count, fields):
    before = user_count()
    response = register(client, **fields)
    assert response.status_code == 400
    assert b"All fields are required" in response.data
    assert user_count() == before


@pytest.mark.parametrize("email", ["notanemail", "a@b", "@x.com", "a@@x.com", "a@.com", "a@x."])
def test_register_invalid_email(client, user_count, email):
    before = user_count()
    response = register(client, email=email)
    assert response.status_code == 400
    assert b"valid email address" in response.data
    assert user_count() == before


def test_failed_register_preserves_name_and_email(client):
    response = register(client, name="Jane Doe", email="jane@example.com", password="secret1")
    html = response.get_data(as_text=True)
    assert response.status_code == 400
    assert 'value="Jane Doe"' in html
    assert 'value="jane@example.com"' in html
    assert "secret1" not in html
