"""Test setup: isolated SQLite file, no Gemini key, no network."""

import os
import tempfile

import pytest

_DB_DIR = tempfile.mkdtemp(prefix="second-brain-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_DIR}/test.db"
os.environ["GEMINI_API_KEY"] = ""
os.environ.pop("GOOGLE_API_KEY", None)
os.environ.pop("ENABLE_BROWSER_AUTOMATION", None)


@pytest.fixture(autouse=True)
def no_gemini(monkeypatch):
    """Fail loudly if any test path reaches the Gemini fallback."""
    from api.services import order_parser

    def _boom(email):
        raise AssertionError(f"Gemini fallback called for {email.get('id')}")

    monkeypatch.setattr(order_parser, "extract_with_gemini", _boom)


@pytest.fixture
def db():
    from api.db.base import Base, SessionLocal, engine, init_db

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
