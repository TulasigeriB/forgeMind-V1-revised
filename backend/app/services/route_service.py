from uuid import UUID

from sqlalchemy.orm import Session

from app.models.feature import ManufacturingFeature
from app.models.operation import ManufacturingOperation
from app.models.project import Project
from app.models.quote import Quote
from app.services.analysis_review import apply_analysis_review
from app.services.process_planner import ProcessPlanner


def _feature_rows(analysis: dict) -> list[dict]:
    rows: list[dict] = []
    feature_types = {
        "bore diameter": "Bore",
        "diameter": "Diameter",
        "thread": "Thread",
        "thread size & pitch": "Thread",
        "thread major diameter": "Thread",
        "thread length": "Thread",
        "slots": "Slot",
        "equally spaced peripheral slots": "Slot",
        "head outer diameter": "Diameter",
        "head length / thickness": "Diameter",
        "hexagonal socket size": "Socket",
        "chamfer": "Chamfer",
    }
    for process_features in analysis["manufacturing_operations"].values():
        for feature in process_features:
            feature_type = feature_types.get(feature["feature"].lower())
            if feature_type is None:
                continue
            dimensions = feature.get("dimensions", [])
            if not dimensions:
                rows.append({
                    "feature_type": feature_type,
                    "dimension": None,
                    "tolerance": "standard",
                    "quantity": feature.get("quantity", 1),
                })
                continue
            for dimension in dimensions:
                if dimension["value"] is None:
                    continue
                fit = next(
                    (
                        item["fit"]
                        for item in analysis["precision_fits"]
                        if item["fit"] and (
                            item["callout"] == dimension["callout"]
                            or item["nominal_size"].split()[0] == str(dimension["value"])
                        )
                    ),
                    None,
                )
                rows.append({
                    "feature_type": feature_type,
                    "dimension": dimension["value"],
                    "tolerance": fit or "standard",
                    "quantity": feature.get("quantity", 1),
                })
    for form_feature in analysis["form_features"]:
        if form_feature.get("feature") == "chamfer":
            rows.append({
                "feature_type": "Chamfer",
                "dimension": form_feature.get("size"),
                "tolerance": "standard",
                "quantity": 1,
            })
        elif form_feature.get("feature") == "perimeter knurling":
            rows.append({
                "feature_type": "Knurl",
                "dimension": None,
                "tolerance": "standard",
                "quantity": 1,
            })
    return rows


class ManufacturingRouteService:
    @staticmethod
    def generate(db: Session, project: Project) -> list[ManufacturingOperation]:
        if not project.analysis_data or not project.analysis_review:
            raise ValueError("Drawing analysis must be reviewed before route generation")
        if project.analysis_review.get("status") != "approved":
            raise ValueError("Engineer approval is required before route generation")

        reviewed_analysis = apply_analysis_review(
            project.analysis_data,
            project.analysis_review["decisions"],
        )
        db.query(ManufacturingFeature).filter(
            ManufacturingFeature.project_id == project.id
        ).delete(synchronize_session=False)
        db.query(ManufacturingOperation).filter(
            ManufacturingOperation.project_id == project.id
        ).delete(synchronize_session=False)
        db.query(Quote).filter(Quote.project_id == project.id).delete(synchronize_session=False)

        features = [
            ManufacturingFeature(project_id=project.id, **feature)
            for feature in _feature_rows(reviewed_analysis)
        ]
        if not features:
            raise ValueError("No accepted manufacturing features are available for route planning")

        db.add_all(features)
        db.flush()
        operations = ProcessPlanner.plan_operations(
            db,
            project.id,
            analysis=reviewed_analysis,
        )
        if not operations:
            raise ValueError("No manufacturing operations could be planned from the approved features")
        db.add_all(operations)
        project.process_plan_status = "generated"
        project.route_review = None
        return operations

    @staticmethod
    def invalidate(db: Session, project_id: UUID) -> None:
        db.query(ManufacturingFeature).filter(
            ManufacturingFeature.project_id == project_id
        ).delete(synchronize_session=False)
        db.query(ManufacturingOperation).filter(
            ManufacturingOperation.project_id == project_id
        ).delete(synchronize_session=False)
        db.query(Quote).filter(Quote.project_id == project_id).delete(synchronize_session=False)
