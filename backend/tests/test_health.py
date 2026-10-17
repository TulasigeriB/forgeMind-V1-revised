from fastapi.testclient import TestClient
import app.api.health as health_module
from app.main import app


class HealthyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, statement):
        return 1


class HealthyEngine:
    def connect(self):
        return HealthyConnection()


class UnhealthyEngine:
    def connect(self):
        raise RuntimeError("private connection details must not leak")


def test_liveness_does_not_depend_on_database():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "forgemind-api"}


def test_readiness_reports_database_available(monkeypatch):
    monkeypatch.setattr(health_module, "get_engine", lambda: HealthyEngine())
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_returns_safe_503_when_database_is_down(monkeypatch):
    monkeypatch.setattr(health_module, "get_engine", lambda: UnhealthyEngine())
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "not_ready", "dependency": "database"}}
    assert "private connection details" not in response.text
