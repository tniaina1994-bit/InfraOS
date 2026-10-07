"""Tests API: sante + updates + openapi generable."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-api.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "testpw123"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_updates_shape():
    r = client.get("/api/v1/updates")
    assert r.status_code == 200 and "pending" in r.json()


def test_openapi_has_paths():
    spec = app.openapi()
    assert "/api/health" in spec["paths"]
