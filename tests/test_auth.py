import pytest


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def test_get_login_renders_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b'action="/login"' in response.data


def test_login_success_demo_user(client):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    with client.session_transaction() as s:
        assert s["user_id"]
        assert s["user_name"] == "Demo User"


def test_login_email_case_and_whitespace(client):
    response = login(client, email=" DEMO@Spendly.com ")
    assert response.status_code == 302


def test_login_newly_registered_user(client):
    client.post("/register", data={"name": "New User", "email": "new@example.com", "password": "password123"})
    response = login(client, email="new@example.com", password="password123")
    assert response.status_code == 302


def test_login_wrong_password(client):
    response = login(client, password="wrongpass")
    assert response.status_code == 401
    assert b"Invalid email or password." in response.data

    with client.session_transaction() as s:
        assert "user_id" not in s


def test_login_unknown_email(client):
    response = login(client, email="nobody@example.com")
    assert response.status_code == 401
    assert b"Invalid email or password." in response.data


@pytest.mark.parametrize("fields", [{"email": ""}, {"password": ""}])
def test_login_missing_fields(client, fields):
    response = login(client, **fields)
    assert response.status_code == 400
    assert b"Email and password are required." in response.data


def test_failed_login_keeps_email_not_password(client):
    response = login(client, password="secretguess")
    assert b'value="demo@spendly.com"' in response.data
    assert b"secretguess" not in response.data


def test_navbar_after_login(client):
    login(client)
    page = client.get("/").get_data(as_text=True)
    assert "Demo User" in page
    assert "Sign out" in page
    assert "Get started" not in page


def test_logout_clears_session(client):
    login(client)
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as s:
        assert "user_id" not in s

    page = client.get("/login").get_data(as_text=True)
    assert "You have been signed out." in page
    assert "Get started" in page


def test_logout_when_signed_out(client):
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_signed_in_redirects_from_login_and_register(client):
    login(client)
    for path in ("/login", "/register"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")
