from fastapi.testclient import TestClient

from market_monitor.app.main import app


def test_web_routes_respond() -> None:
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/api/articles?window=24h").status_code == 200
    assert client.get("/api/digest?window=7d").status_code == 200
    digest_payload = client.get("/api/digest?window=7d").json()
    assert "digest" in digest_payload
    assert "top_stories" in digest_payload["digest"]
    assert digest_payload["digest"]["window"] == "7d"
