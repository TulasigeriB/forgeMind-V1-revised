import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.engineering_file import EngineeringFile
from app.models.feature import ManufacturingFeature
from app.models.operation import ManufacturingOperation
from app.models.project import Project
from app.models.rfq import RFQ
from app.models.customer import Customer
from app.services.drawing_intelligence import DrawingIntelligenceService
from app.services.route_service import ManufacturingRouteService

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.worker.process_geometry_analysis")
def process_geometry_analysis(self, project_id: str):
    project_uuid = UUID(project_id)
    db = SessionLocal()
    try:
        project = db.get(Project, project_uuid)
        if project is None:
            raise ValueError(f"Project {project_id} does not exist")

        files = db.query(EngineeringFile).filter(
            EngineeringFile.project_id == project_uuid
        ).order_by(EngineeringFile.created_at).all()
        if not files:
            raise ValueError(f"Project {project_id} has no uploaded engineering drawings")

        self.update_state(state="PROGRESS", meta={"progress": 10, "step": "Reading drawing files"})
        analysis = DrawingIntelligenceService.analyze_files(
            files=files,
            project_part_number=project.part_number,
            project_material=project.material_spec,
        )

        self.update_state(state="PROGRESS", meta={"progress": 70, "step": "Classifying dimensions and features"})
        ManufacturingRouteService.invalidate(db, project_uuid)
        project.analysis_data = analysis
        project.analysis_review = None
        project.route_review = None
        project.process_plan_status = "not_generated"
        project.status = "analysis_ready"
        db.commit()

        return {
            "status": "analysis_ready",
            "callouts": sum(len(feature.get("dimensions", []))
                            for process in analysis["manufacturing_operations"].values()
                            for feature in process),
            "review_flags": len(analysis["review_flags"]),
        }
    except Exception:
        db.rollback()
        failed_project = db.get(Project, project_uuid)
        if failed_project is not None:
            failed_project.status = "analysis_failed"
            db.commit()
        logger.exception("Drawing analysis failed for project %s", project_id)
        raise
    finally:
        db.close()
