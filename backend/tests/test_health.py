from fastapi.testclient import TestClient

from app.main import create_app


def test_health_and_shutdown_do_not_create_a_database_engine(monkeypatch, isolated_settings):
    def fail_if_engine_is_created(*args, **kwargs):
        raise AssertionError("Liveness must not depend on PostgreSQL")

    monkeypatch.setattr("app.db.session.create_engine", fail_if_engine_is_created)
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "seo-tool-api"}
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert client.get("/docs").status_code == 200


def test_unlisted_browser_origin_does_not_get_cors_access(isolated_settings):
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health", headers={"Origin": "https://unlisted.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
