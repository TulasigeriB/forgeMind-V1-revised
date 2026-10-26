from sqlalchemy.orm import Session
from app.models.feature import CostTemplate
from app.models.operation import ManufacturingOperation
from app.models.project import Project
from app.models.quote import Quote
from app.models.rfq import RFQ
from app.schemas.feature import CostTemplateCreate
from uuid import UUID

class CostingService:
    @staticmethod
    def create_template(db: Session, template: CostTemplateCreate):
        db_template = CostTemplate(**template.model_dump())
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return db_template

    @staticmethod
    def create_project_quote(db: Session, project_id: UUID) -> Quote:
        project = db.get(Project, project_id)
        if project is None:
            raise ValueError("Project not found")
        if project.analysis_review is None or project.analysis_review.get("status") != "approved":
            raise ValueError("Engineer-approved drawing analysis is required before quotation")
        if project.process_plan_status != "approved":
            raise ValueError("Engineer-approved manufacturing routes are required before quotation")

        rfq = db.get(RFQ, project.rfq_id)
        if rfq is None:
            raise ValueError("Project RFQ was not found")
        operations = db.query(ManufacturingOperation).filter(
            ManufacturingOperation.project_id == project_id
        ).order_by(ManufacturingOperation.sequence_order).all()
        if not operations:
            raise ValueError("No manufacturing route operations are available for quotation")

        order_quantity = rfq.quantity
        breakdown = [
            {
                "operation": operation.operation_name,
                "quantity": order_quantity,
                "unit_cost": round(operation.estimated_cost, 2),
                "extended_cost": round(operation.estimated_cost * order_quantity, 2),
                "unit_time_minutes": round(operation.estimated_time_minutes, 2),
                "extended_time_minutes": round(operation.estimated_time_minutes * order_quantity, 2),
                "machine_type": operation.machine_type,
            }
            for operation in operations
        ]
        assumptions = [
            "Per-part operation costs and any provided cycle times are multiplied by the RFQ order quantity.",
            "Material, labor, overhead, scrap, taxes, and shipping are excluded unless included in route estimates.",
            "This is an estimate based on the engineer-approved manufacturing route, not an approved customer quote.",
        ]
        if any(operation.operation_name.startswith("Raw Material (18-8") for operation in operations):
            assumptions.append(
                "Per-unit process rates use the supplied 18-8 stainless fastener baseline for a 1,000-piece batch; "
                "validate material usage, labor, overhead, yield, and tooling against current shop data."
            )
        if any(operation.estimated_time_minutes == 0 for operation in operations):
            assumptions.append(
                "Cycle time was not supplied for one or more route steps and is excluded from the total time estimate."
            )
        quote = Quote(
            project_id=project_id,
            order_quantity=order_quantity,
            total_cost=round(sum(item["extended_cost"] for item in breakdown), 2),
            total_time_minutes=round(sum(item["extended_time_minutes"] for item in breakdown), 2),
            status="estimate",
            details={"assumptions": assumptions, "breakdown": breakdown},
        )
        db.add(quote)
        project.status = "quoted"
        db.commit()
        db.refresh(quote)
        return quote
