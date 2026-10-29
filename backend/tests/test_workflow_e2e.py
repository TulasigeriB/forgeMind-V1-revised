from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.services.analysis_review import get_review_targets
from app import worker
from app.api import files as files_api
from app.api import projects as projects_api


@pytest.fixture
def workflow_database(tmp_path, monkeypatch):
    # These workflow tests focus on manufacturing behavior, not JWT authentication.
    monkeypatch.setattr(settings, "AUTH_DISABLED_FOR_TESTING", True)
    database_path = tmp_path / "workflow.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(files_api, "UPLOAD_DIR", Path(settings.UPLOAD_DIR))
    files_api.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    monkeypatch.setattr(worker.process_geometry_analysis, "update_state", lambda **kwargs: None)
    monkeypatch.setattr(
        projects_api.celery_app,
        "send_task",
        lambda *args, **kwargs: SimpleNamespace(id="test-analysis-task"),
    )
    app.dependency_overrides[get_db] = override_get_db

    try:
        yield session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def make_sample_drawing(path: Path):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((40, 40), "PART NUMBER: TEST-SHAFT-001")
    page.insert_text((40, 60), "MATERIAL: SS-304")
    page.insert_text((40, 80), "DIMENSIONS ARE IN MILLIMETERS")
    page.insert_text((80, 140), "Ø10.00")
    page.insert_text((80, 180), "M6 x 1.0 THREAD")
    page.draw_line((70, 145), (160, 145))
    page.draw_line((70, 185), (160, 185))
    document.save(path)
    document.close()


def make_socket_head_screw_drawing(path: Path):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((40, 40), "PART NUMBER: 92200A620")
    page.insert_text((40, 60), "DESCRIPTION: Steel Socket Head Screw")
    page.insert_text((40, 80), "MATERIAL: Mil. Spec. 18-8 Stainless Steel")
    page.insert_text((40, 100), "DIMENSIONS ARE IN INCHES")
    page.insert_text((80, 130), "HEAD OD 0.469in")
    page.insert_text((80, 150), "HEAD THICKNESS 0.313in")
    page.insert_text((80, 170), 'HEX SOCKET 1/4"')
    page.insert_text((80, 190), "THREAD LENGTH 0.375in")
    page.insert_text((80, 210), '5/16"-18 UNRC')
    page.insert_text((80, 230), "DIAMETRAL KNURLING")
    page.insert_text((310, 160), "0.313in")
    page.draw_line((324, 140), (324, 190))
    for y in range(140, 241, 20):
        page.draw_line((70, y), (200, y))
    document.save(path)
    document.close()


def test_customer_to_approved_quote_workflow(tmp_path, workflow_database):
    drawing_path = tmp_path / "test-shaft.pdf"
    make_sample_drawing(drawing_path)

    with TestClient(app) as client:
        customer_response = client.post(
            "/api/v1/customers",
            json={"name": "Workflow Test Customer", "contact_email": "buyer@example.com"},
        )
        assert customer_response.status_code == 200
        customer_id = customer_response.json()["id"]

        rfq_response = client.post(
            "/api/v1/rfqs",
            json={"customer_id": customer_id, "quantity": 10, "priority": "normal"},
        )
        assert rfq_response.status_code == 200

        project_response = client.post(
            "/api/v1/projects",
            json={
                "rfq_id": rfq_response.json()["id"],
                "part_number": "TEST-SHAFT-001",
                "material_spec": "SS-304",
            },
        )
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]

        with drawing_path.open("rb") as drawing:
            upload_response = client.post(
                "/api/v1/upload",
                params={"project_id": project_id},
                files={"file": ("test-shaft.pdf", drawing, "application/pdf")},
            )
        assert upload_response.status_code == 200
        assert len(client.get(f"/api/v1/projects/{project_id}/files").json()) == 1

        task_response = client.post(f"/api/v1/projects/{project_id}/analyze")
        assert task_response.status_code == 200
        assert task_response.json()["task_id"] == "test-analysis-task"
        worker.process_geometry_analysis.run(project_id)

        analysis_response = client.get(f"/api/v1/projects/{project_id}/analysis")
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        assert analysis_data["status"] == "analysis_ready"
        assert analysis_data["analysis"]["part_identifier"] == "TEST-SHAFT-001"
        assert analysis_data["analysis"]["units"] == "mm"

        review_targets = get_review_targets(analysis_data["analysis"])
        assert review_targets
        review_response = client.put(
            f"/api/v1/projects/{project_id}/analysis/review",
            json={
                "status": "approved",
                "decisions": [
                    {"target_id": target_id, "decision": "accepted"}
                    for target_id in review_targets
                ],
            },
        )
        assert review_response.status_code == 200
        assert review_response.json()["review"]["status"] == "approved"

        route_response = client.post(f"/api/v1/projects/{project_id}/routes")
        if route_response.status_code == 409:
            assert "No cost template is configured" in route_response.json()["detail"]
            for feature_type in ("Diameter", "Thread"):
                template_response = client.post(
                    "/api/v1/templates",
                    json={
                        "feature_type": feature_type,
                        "base_cost_per_unit": 2.0,
                        "time_per_unit_minutes": 5.0,
                        "precision_multiplier": 1.5,
                    },
                )
                assert template_response.status_code == 200
            route_response = client.post(f"/api/v1/projects/{project_id}/routes")
        assert route_response.status_code == 200
        operations = route_response.json()
        assert operations

        route_review_response = client.put(
            f"/api/v1/projects/{project_id}/routes/review",
            json={
                "status": "approved",
                "comment": "Approved for quotation",
                "operations": [
                    {
                        "operation_id": operation["id"],
                        "operation_name": operation["operation_name"],
                        "sequence_order": operation["sequence_order"],
                        "estimated_time_minutes": operation["estimated_time_minutes"],
                        "estimated_cost": operation["estimated_cost"],
                        "machine_type": operation["machine_type"],
                    }
                    for operation in operations
                ],
            },
        )
        assert route_review_response.status_code == 200
        assert route_review_response.json()["process_plan_status"] == "approved"

        quote_response = client.post(f"/api/v1/projects/{project_id}/quote")
        assert quote_response.status_code == 200
        quote = quote_response.json()
        assert quote["order_quantity"] == 10
        assert quote["total_cost"] == pytest.approx(
            sum(item["extended_cost"] for item in quote["breakdown"])
        )
        assert quote["total_time_minutes"] == pytest.approx(
            sum(item["extended_time_minutes"] for item in quote["breakdown"])
        )
        assert all(item["quantity"] == quote["order_quantity"] for item in quote["breakdown"])
        assert all(
            item["extended_cost"] == pytest.approx(item["unit_cost"] * item["quantity"])
            for item in quote["breakdown"]
        )
        assert all(
            item["extended_time_minutes"] == pytest.approx(item["unit_time_minutes"] * item["quantity"])
            for item in quote["breakdown"]
        )
        persisted_quote = client.get(f"/api/v1/projects/{project_id}/quote").json()
        assert persisted_quote["id"] == quote["id"]
        assert persisted_quote["total_cost"] == pytest.approx(quote["total_cost"])
        assert persisted_quote["breakdown"] == quote["breakdown"]


def test_socket_head_screw_workflow_uses_process_cost_baseline(tmp_path, workflow_database):
    drawing_path = tmp_path / "socket-head-screw.pdf"
    make_socket_head_screw_drawing(drawing_path)

    with TestClient(app) as client:
        customer = client.post(
            "/api/v1/customers",
            json={"name": "Fastener Test Customer", "contact_email": "fastener@example.com"},
        )
        rfq = client.post(
            "/api/v1/rfqs",
            json={"customer_id": customer.json()["id"], "quantity": 1000, "priority": "normal"},
        )
        project = client.post(
            "/api/v1/projects",
            json={
                "rfq_id": rfq.json()["id"],
                "part_number": "92200A620",
                "material_spec": "Mil. Spec. 18-8 Stainless Steel",
            },
        )
        project_id = project.json()["id"]

        with drawing_path.open("rb") as drawing:
            upload = client.post(
                "/api/v1/upload",
                params={"project_id": project_id},
                files={"file": ("socket-head-screw.pdf", drawing, "application/pdf")},
            )
        assert upload.status_code == 200
        assert client.post(f"/api/v1/projects/{project_id}/analyze").status_code == 200
        worker.process_geometry_analysis.run(project_id)

        analysis = client.get(f"/api/v1/projects/{project_id}/analysis").json()["analysis"]
        assert analysis["part_identifier"] == "92200A620"
        assert analysis["metadata_and_notes"][0]["material"] == "Mil. Spec. 18-8 Stainless Steel"
        analyzed_dimensions = [
            (feature["feature"], dimension)
            for features in analysis["manufacturing_operations"].values()
            for feature in features
            for dimension in feature["dimensions"]
        ]
        assert sum(dimension["value"] == 0.313 for _, dimension in analyzed_dimensions) == 2
        assert {feature for feature, _ in analyzed_dimensions} >= {
            "head outer diameter",
            "head length / thickness",
            "thread length",
            "thread major diameter",
            "thread size & pitch",
            "hexagonal socket size",
        }
        review_targets = get_review_targets(analysis)
        review = client.put(
            f"/api/v1/projects/{project_id}/analysis/review",
            json={
                "status": "approved",
                "decisions": [
                    {"target_id": target_id, "decision": "accepted"}
                    for target_id in review_targets
                ],
            },
        )
        assert review.status_code == 200

        routes = client.post(f"/api/v1/projects/{project_id}/routes")
        assert routes.status_code == 200
        operations = routes.json()
        assert [operation["operation_name"] for operation in operations] == [
            "Raw Material (18-8 Stainless Steel Wire)",
            "Cold Heading & Socket Punching",
            "Turning, Facing & Head Profiling",
            "Perimeter Knurling",
            "Thread Rolling",
            "Chemical Passivation & Cleaning",
            "Quality Control & Packaging",
        ]
        assert [operation["estimated_cost"] for operation in operations] == pytest.approx(
            [0.18, 0.10, 0.12, 0.06, 0.08, 0.07, 0.05]
        )
        assert all(operation["estimated_time_minutes"] == 0 for operation in operations)

        route_review = client.put(
            f"/api/v1/projects/{project_id}/routes/review",
            json={
                "status": "approved",
                "operations": [
                    {
                        "operation_id": operation["id"],
                        "operation_name": operation["operation_name"],
                        "sequence_order": operation["sequence_order"],
                        "estimated_time_minutes": operation["estimated_time_minutes"],
                        "estimated_cost": operation["estimated_cost"],
                        "machine_type": operation["machine_type"],
                    }
                    for operation in operations
                ],
            },
        )
        assert route_review.status_code == 200

        quote_response = client.post(f"/api/v1/projects/{project_id}/quote")
        assert quote_response.status_code == 200
        quote = quote_response.json()
        assert quote["total_cost"] == pytest.approx(660)
        assert quote["total_time_minutes"] == 0
        assert sum(item["unit_cost"] for item in quote["breakdown"]) == pytest.approx(0.66)
        assert any("1,000-piece batch" in item for item in quote["assumptions"])
        assert any("Cycle time was not supplied" in item for item in quote["assumptions"])
