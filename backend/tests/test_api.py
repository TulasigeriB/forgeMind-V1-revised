import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import UUID, uuid4

from app.main import app
from app.db.session import Base, get_db
from app.core.security import create_access_token
from app.core.config import settings
from app.models.engineering_file import EngineeringFile
from app.models.project import Project as ProjectModel
from app.models.operation import ManufacturingOperation
from app.models.quote import Quote

# --- Configuration ---
# In production, these would come from a .env.test file
TEST_DATABASE_URL = "postgresql+psycopg://postgres:adminforgemind@localhost:5432/forgemind_db_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Fixtures ---
@pytest.fixture(autouse=True)
def enable_auth_bypass_for_legacy_tests(monkeypatch):
    """Legacy API behavior tests opt into the auth bypass explicitly.

    Security-boundary tests override this setting to False and exercise real JWT checks.
    """
    monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", True)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize the test database schema once per session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Provides a clean database session for every test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """FastAPI TestClient with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth_token():
    """Generates a valid JWT token for authenticated requests."""
    # Mocking a user 'test_user'
    return create_access_token(data={"sub": "test_user"})

# --- Test Suite ---

class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "version": "0.1.0"}

class TestSecurityBoundaries:
    def test_customer_directory_requires_token(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", False)

        response = client.get("/api/v1/customers")

        assert response.status_code == 401

    def test_protected_route_no_token(self, client, monkeypatch):
        """Ensure protected routes reject requests without a token."""
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", False)
        response = client.put(
            f"/api/v1/projects/{uuid4()}/analysis/review",
            json={"status": "in_review", "decisions": []},
        )
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_protected_route_invalid_token(self, client, monkeypatch):
        """Ensure protected routes reject malformed tokens."""
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", False)
        response = client.put(
            f"/api/v1/projects/{uuid4()}/analysis/review",
            json={"status": "in_review", "decisions": []},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("path", [
        "/api/v1/customers",
        "/api/v1/projects",
        "/api/v1/templates",
    ])
    def test_data_routes_reject_missing_token(self, client, monkeypatch, path):
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", False)
        response = client.get(path)
        assert response.status_code == 401

    def test_customer_creation_rejects_missing_token(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", False)
        response = client.post(
            "/api/v1/customers",
            json={"name": "Unauthorized", "contact_email": "unauthorized@example.com"},
        )
        assert response.status_code == 401

    def test_protected_route_without_token_in_testing_mode(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", True)

        response = client.get("/api/v1/projects")

        assert response.status_code == 200

class TestCustomerAPI:
    def test_create_customer_success(self, client, auth_token):
        payload = {
            "name": "Industrial Corp",
            "contact_email": "contact@industrial.com",
            "address": "123 Machine Way"
        }
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post("/api/v1/customers", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == payload["name"]
        assert "id" in data
        # Verify UUID format (roughly)
        assert len(data["id"]) == 36

    def test_list_customers(self, client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        client.post(
            "/api/v1/customers",
            json={"name": "Directory Customer", "contact_email": "directory@example.com"},
            headers=headers,
        )

        response = client.get("/api/v1/customers", headers=headers)

        assert response.status_code == 200
        assert response.json()[0]["name"] == "Directory Customer"

    def test_create_customer_invalid_email(self, client, auth_token):
        payload = {
            "name": "Bad Email Corp",
            "contact_email": "not-an-email",
            "address": "123 Machine Way"
        }
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post("/api/v1/customers", json=payload, headers=headers)
        assert response.status_code == 422 # Validation Error

    def test_update_customer(self, client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        created = client.post(
            "/api/v1/customers",
            json={"name": "Before Update", "contact_email": "before@example.com"},
            headers=headers,
        )

        response = client.patch(
            f"/api/v1/customers/{created.json()['id']}",
            json={"name": "After Update", "address": "1 Factory Road"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "After Update"
        assert response.json()["address"] == "1 Factory Road"

class TestAnalysisReviewPersistence:
    def test_corrected_and_rejected_review_survives_reload_without_mutating_source(self, client, db_session, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        customer = client.post(
            "/api/v1/customers",
            json={"name": "Review Persistence Customer", "contact_email": "review-persist@example.com"},
            headers=headers,
        ).json()
        rfq = client.post(
            "/api/v1/rfqs",
            json={"customer_id": customer["id"], "quantity": 1},
            headers=headers,
        ).json()
        project = client.post(
            "/api/v1/projects",
            json={"rfq_id": rfq["id"], "part_number": "REVIEW-001"},
            headers=headers,
        ).json()
        project_uuid = UUID(project["id"])
        source_analysis = {
            "part_identifier": "REVIEW-001",
            "units": "mm",
            "manufacturing_operations": {
                "turning": [{"feature": "diameter", "dimensions": [
                    {"callout": "Ø10", "value": 10.0, "units": "mm"},
                    {"callout": "Ø99", "value": 99.0, "units": "mm"},
                ]}],
                "milling": [],
            },
            "precision_fits": [], "geometric_tolerances": [], "form_features": [],
            "critical_operations": [], "inspection_checklist": [],
            "quality_document_templates": {}, "metadata_and_notes": [], "review_flags": [],
        }
        db_project = db_session.get(ProjectModel, project_uuid)
        db_project.analysis_data = source_analysis
        db_project.status = "analysis_ready"
        db_session.commit()

        response = client.put(
            f"/api/v1/projects/{project_uuid}/analysis/review",
            json={"status": "changes_requested", "decisions": [
                {"target_id": "manufacturing_operations.turning.0.dimensions.0", "decision": "corrected", "corrected_value": 10.5, "corrected_callout": "Ø10.5"},
                {"target_id": "manufacturing_operations.turning.0.dimensions.1", "decision": "rejected"},
            ]},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.expire_all()
        reloaded = db_session.get(ProjectModel, project_uuid)
        assert reloaded.analysis_review["status"] == "changes_requested"
        decisions = {item["target_id"]: item for item in reloaded.analysis_review["decisions"]}
        assert decisions["manufacturing_operations.turning.0.dimensions.0"]["corrected_value"] == 10.5
        assert decisions["manufacturing_operations.turning.0.dimensions.1"]["decision"] == "rejected"
        # The raw extraction remains immutable; route generation applies review decisions to a copy.
        assert reloaded.analysis_data["manufacturing_operations"]["turning"][0]["dimensions"][0]["value"] == 10.0
        assert len(reloaded.analysis_data["manufacturing_operations"]["turning"][0]["dimensions"]) == 2


class TestProjectDeletion:
    def test_delete_project_removes_database_records_and_physical_drawing(self, client, db_session, auth_token, tmp_path, monkeypatch):
        from app.api import files as files_api

        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
        monkeypatch.setattr(files_api, "UPLOAD_DIR", tmp_path)
        headers = {"Authorization": f"Bearer {auth_token}"}
        customer = client.post(
            "/api/v1/customers",
            json={"name": "Delete Test Customer", "contact_email": "delete-test@example.com"},
            headers=headers,
        ).json()
        rfq = client.post(
            "/api/v1/rfqs",
            json={"customer_id": customer["id"], "quantity": 2},
            headers=headers,
        ).json()
        project = client.post(
            "/api/v1/projects",
            json={"rfq_id": rfq["id"], "part_number": "DELETE-001"},
            headers=headers,
        ).json()

        stored_file = tmp_path / "delete-me.pdf"
        stored_file.write_bytes(b"%PDF-1.4 test")
        project_uuid = UUID(project["id"])
        engineering_file = EngineeringFile(
            project_id=project_uuid, file_type="PDF", storage_path=str(stored_file), status="uploaded"
        )
        db_session.add(engineering_file)
        db_session.commit()
        file_id = engineering_file.id
        project_id = project["id"]

        response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)

        assert response.status_code == 204
        assert not stored_file.exists()
        assert db_session.get(ProjectModel, project_uuid) is None
        assert db_session.get(EngineeringFile, file_id) is None
        assert db_session.query(ManufacturingOperation).filter_by(project_id=project_uuid).count() == 0
        assert db_session.query(Quote).filter_by(project_id=project_uuid).count() == 0


class TestProjectWorkflow:
    def test_full_project_lifecycle(self, client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}

        # 1. Create Customer
        cust_resp = client.post("/api/v1/customers",
                               json={"name": "CNC Ltd", "contact_email": "cnc@ltd.com"},
                               headers=headers)
        customer_id = cust_resp.json()["id"]

        # 2. Create RFQ
        rfq_resp = client.post("/api/v1/rfqs",
                                json={"customer_id": customer_id, "quantity": 10},
                                headers=headers)
        rfq_id = rfq_resp.json()["id"]

        # 3. Create Project
        proj_resp = client.post("/api/v1/projects",
                                json={"rfq_id": rfq_id, "part_number": "PART-001"},
                                headers=headers)
        project_id = proj_resp.json()["id"]
        assert proj_resp.json()["customer_name"] == "CNC Ltd"

        # 4. Get Project
        get_resp = client.get(f"/api/v1/projects/{project_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["part_number"] == "PART-001"

        analysis_resp = client.get(f"/api/v1/projects/{project_id}/analysis", headers=headers)
        assert analysis_resp.status_code == 200
        assert analysis_resp.json()["analysis"] is None

    def test_get_nonexistent_project(self, client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/projects/{fake_id}", headers=headers)
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]

class TestFileAPI:
    def test_upload_file_unauthorized(self, client, monkeypatch):
        # Attempt upload without token
        monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", False)
        response = client.post(
            "/api/v1/upload",
            params={"project_id": str(uuid4())},
            files={"file": ("test.txt", b"test content", "text/plain")},
        )
        assert response.status_code == 401

    def test_upload_unsupported_type(self, client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post(
            "/api/v1/upload",
            params={"project_id": str(uuid4())},
            files={"file": ("dummy.txt", b"hello", "text/plain")},
            headers=headers,
        )

        assert response.status_code == 415
        assert "Only PDF drawings are currently supported" in response.json()["detail"]

    def test_analyze_upload_persists_analysis_and_serves_file(self, client, auth_token, monkeypatch):
        headers = {"Authorization": f"Bearer {auth_token}"}
        customer = client.post(
            "/api/v1/customers",
            json={"name": "Drawing Customer", "contact_email": "drawing@example.com"},
            headers=headers,
        ).json()
        rfq = client.post(
            "/api/v1/rfqs",
            json={"customer_id": customer["id"], "quantity": 1},
            headers=headers,
        ).json()
        project = client.post(
            "/api/v1/projects",
            json={"rfq_id": rfq["id"], "part_number": "DRAW-001", "material_spec": "Steel"},
            headers=headers,
        ).json()
        expected_analysis = {
            "part_identifier": "DRAW-001",
            "units": "mm",
            "manufacturing_operations": {"turning": [], "milling": []},
            "precision_fits": [],
            "geometric_tolerances": [],
            "form_features": [],
            "critical_operations": [],
            "inspection_checklist": [],
            "quality_document_templates": {},
            "metadata_and_notes": [],
            "review_flags": [],
        }
        monkeypatch.setattr(
            "app.api.files.DrawingIntelligenceService.analyze_files",
            lambda **kwargs: expected_analysis,
        )

        response = client.post(
            "/api/v1/files/analyze",
            data={"project_id": project["id"]},
            files={"file": ("drawing.pdf", b"%PDF-1.4 test drawing", "application/pdf")},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == expected_analysis
        project_analysis = client.get(f"/api/v1/projects/{project['id']}/analysis", headers=headers)
        assert project_analysis.json()["analysis"] == expected_analysis
        files = client.get(f"/api/v1/projects/{project['id']}/files", headers=headers).json()
        assert len(files) == 1
        assert files[0]["status"] == "analyzed"
        content = client.get(f"/api/v1/files/{files[0]['id']}/content", headers=headers)
        assert content.status_code == 200
        assert content.content == b"%PDF-1.4 test drawing"

    def test_analyze_upload_rejects_invalid_pdf(self, client, auth_token):
        headers = {"Authorization": f"Bearer {auth_token}"}
        customer = client.post(
            "/api/v1/customers",
            json={"name": "Invalid Drawing Customer", "contact_email": "invalid-drawing@example.com"},
            headers=headers,
        ).json()
        rfq = client.post(
            "/api/v1/rfqs",
            json={"customer_id": customer["id"], "quantity": 1},
            headers=headers,
        ).json()
        project = client.post(
            "/api/v1/projects",
            json={"rfq_id": rfq["id"], "part_number": "DRAW-002"},
            headers=headers,
        ).json()

        response = client.post(
            "/api/v1/files/analyze",
            data={"project_id": project["id"]},
            files={"file": ("drawing.pdf", b"not a pdf", "application/pdf")},
            headers=headers,
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "The uploaded file is not a valid PDF"
