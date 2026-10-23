def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def register_and_login(client, name="New User", email="new@example.com", password="password123"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    return login(client, email=email, password=password)


def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    page = client.get("/login").get_data(as_text=True)
    assert "Please sign in to view your profile." in page


def test_profile_stale_session_is_cleared(client):
    with client.session_transaction() as s:
        s["user_id"] = 9999
        s["user_name"] = "Ghost"

    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as s:
        assert "user_id" not in s


def test_profile_demo_user(client):
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Demo User" in page
    assert "demo@spendly.com" in page
    assert "Member since" in page
    assert "₹330.78" in page
    assert '<span class="stat-value">8</span>' in page


def test_profile_hides_password_hash(client):
    login(client)
    page = client.get("/profile").get_data(as_text=True)
    assert "scrypt:" not in page
    assert "pbkdf2:" not in page


def test_profile_categories_sorted_by_total(client):
    login(client)
    page = client.get("/profile").get_data(as_text=True)
    assert page.count('class="category-row"') == 7
    assert page.index("₹89.99") < page.index("₹84.80")


def test_profile_recent_expenses_newest_first(client):
    login(client)
    page = client.get("/profile").get_data(as_text=True)
    assert page.index("Groceries") < page.index("Lunch")


def test_profile_empty_state_for_new_user(client):
    register_and_login(client)
    response = client.get("/profile")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "New User" in page
    assert "No expenses yet" in page
    assert "₹0.00" in page


def test_profile_does_not_leak_other_users_expenses(client):
    register_and_login(client)
    page = client.get("/profile").get_data(as_text=True)
    assert "Groceries" not in page
    assert "₹330.78" not in page


def test_navbar_name_links_to_profile(client):
    login(client)
    page = client.get("/").get_data(as_text=True)
    assert 'href="/profile" class="nav-user"' in page
