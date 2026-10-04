from __future__ import annotations

import json

from fastapi.testclient import TestClient

from harness.api import app, store


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_events_for_missing_run():
    client = TestClient(app)
    response = client.get("/runs/not-a-real-run/events")
    assert response.status_code == 404
