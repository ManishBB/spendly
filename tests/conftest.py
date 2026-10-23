import pytest

import database.db as db
from app import app as flask_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def user_count(app):
    def count():
        conn = db.get_db()
        try:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            conn.close()

    return count
