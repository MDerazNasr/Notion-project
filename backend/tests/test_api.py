"""API integration tests for the NotionPulse demo workflow."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402


client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_demo_returns_ranked_pages() -> None:
    response = client.post("/score/demo")

    assert response.status_code == 200
    body = response.json()

    assert body["workspace_id"] == "ws-notionpulse-demo"
    assert body["source"] == "demo"
    assert body["page_count"] == 28
    assert len(body["pages"]) == 28
    assert body["pages"][0]["reliability_score"] >= body["pages"][-1]["reliability_score"]
    assert body["pages"][0]["score_band"] in {"green", "amber", "red"}
    assert body["model"]["evaluation_target"] == (
        "minimize Brier score on self-supervised stale labels"
    )


def test_score_endpoint_supports_demo_mode() -> None:
    response = client.post("/score", json={"demo_mode": True})

    assert response.status_code == 200
    body = response.json()

    assert body["source"] == "demo"
    assert body["page_count"] == 28


def test_scores_endpoint_returns_cached_demo_run() -> None:
    client.post("/score/demo")
    response = client.get("/scores?source=demo")

    assert response.status_code == 200
    body = response.json()

    assert body["source"] == "demo"
    assert len(body["pages"]) == 28


def test_page_detail_uses_latest_demo_run() -> None:
    score_response = client.post("/score/demo")
    page_id = score_response.json()["pages"][0]["page_id"]

    response = client.get(f"/page/{page_id}")

    assert response.status_code == 200
    body = response.json()

    assert body["page_id"] == page_id
    assert len(body["structural_features"]) == 5
    assert len(body["semantic_features"]) == 3
    assert body["score_band"] in {"green", "amber", "red"}


def test_graph_returns_nodes_and_edges() -> None:
    client.post("/score/demo")
    response = client.get("/graph")

    assert response.status_code == 200
    body = response.json()

    assert body["workspace_id"] == "ws-notionpulse-demo"
    assert len(body["nodes"]) == 28
    assert len(body["edges"]) > 0
