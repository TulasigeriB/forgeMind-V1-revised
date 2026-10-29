from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from pydantic import EmailStr
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.project_service import ProjectService
from app.services.costing_service import CostingService
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate
from app.schemas.rfq import RFQ, RFQCreate
from app.schemas.project import Project, ProjectCreate
from app.schemas.feature import ManufacturingFeature as FeatureSchema, CostTemplate, CostTemplateCreate
from app.schemas.analysis import (
    ProcessPlanReviewUpdate,
    ProjectAnalysisResponse,
)
from app.schemas.analysis import (
    ProjectAnalysisReview,
    ProjectAnalysisReviewUpdate,
)
from app.models.feature import ManufacturingFeature, CostTemplate as CostTemplateModel
from app.models.operation import ManufacturingOperation
from app.models.engineering_file import EngineeringFile
from app.core.celery_app import celery_app
from app.core.security import get_current_user
from app.services.analysis_review import get_review_targets
from app.services.route_service import ManufacturingRouteService
from app.models.project import Project as ProjectModel
from app.models.customer import Customer as CustomerModel
from app.models.rfq import RFQ as RFQModel
from app.models.quote import Quote
from app.schemas.quote import QuoteResponse
from app.schemas.operation import ManufacturingOperation as OperationSchema
from uuid import UUID
# ... other imports ...

router = APIRouter()


def _quote_response(quote: Quote) -> dict:
    return {
        "id": quote.id,
        "project_id": quote.project_id,
        "order_quantity": quote.order_quantity,
        "status": quote.status,
        "total_cost": quote.total_cost,
        "total_time_minutes": quote.total_time_minutes,
        "assumptions": quote.details["assumptions"],
        "breakdown": quote.details["breakdown"],
        "created_at": quote.created_at,
    }


@router.post("/customers", response_model=Customer)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    try:
        return ProjectService.create_customer(db, customer)
    except ProjectService.CustomerAlreadyExistsError as error:
        raise HTTPException(status_code=409, detail="A customer with this email already exists") from error

@router.get("/customers", response_model=list[Customer])
def list_customers(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return ProjectService.get_all_customers(db)

@router.get("/customers/by-email", response_model=Customer)
def get_customer_by_email(email: EmailStr, db: Session = Depends(get_db)):
    customer = ProjectService.get_customer_by_email(db, email)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.patch("/customers/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: UUID,
    customer: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    try:
        updated_customer = ProjectService.update_customer(db, customer_id, customer)
    except ProjectService.CustomerAlreadyExistsError as error:
        raise HTTPException(status_code=409, detail="A customer with this email already exists") from error
    if updated_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated_customer

@router.post("/rfqs", response_model=RFQ)
def create_rfq(rfq: RFQCreate, db: Session = Depends(get_db)):
    return ProjectService.create_rfq(db, rfq)

@router.post("/projects", response_model=Project)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    return ProjectService.create_project(db, project)

@router.post("/templates", response_model=CostTemplate)
def create_cost_template(template: CostTemplateCreate, db: Session = Depends(get_db)):
    existing = db.query(CostTemplateModel).filter(CostTemplateModel.feature_type == template.feature_type).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A cost template for this feature type already exists")

    db_template = CostTemplateModel(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.get("/templates", response_model=list[CostTemplate])
def list_cost_templates(db: Session = Depends(get_db)):
    return db.query(CostTemplateModel).order_by(CostTemplateModel.feature_type).all()

@router.get("/projects", response_model=list[Project])
def list_projects(db: Session = Depends(get_db)):
    return ProjectService.get_all_projects(db)

@router.get("/projects/{project_id}", response_model=Project)
def read_project(project_id: UUID, db: Session = Depends(get_db)):
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/projects/{project_id}/analyze")
def analyze_project_geometry(project_id: UUID, db: Session = Depends(get_db)):
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    has_pdf = db.query(EngineeringFile.id).filter(
        EngineeringFile.project_id == project_id,
        EngineeringFile.file_type == "PDF",
    ).first()
    if not has_pdf:
        raise HTTPException(status_code=409, detail="Upload a PDF drawing before starting analysis")

    project.status = "analyzing"
    project.analysis_review = None
    project.route_review = None
    project.process_plan_status = "not_generated"
    db.commit()
    try:
        task = celery_app.send_task("app.worker.process_geometry_analysis", args=[str(project_id)])
    except Exception as error:
        project.status = "uploaded"
        db.commit()
        raise HTTPException(status_code=503, detail="Unable to queue drawing analysis") from error
    return {"task_id": task.id, "status": "Analysis started"}

@router.get("/projects/{project_id}/analysis", response_model=ProjectAnalysisResponse)
def get_project_analysis(project_id: UUID, db: Session = Depends(get_db)):
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": str(project.id),
        "status": project.status,
        "analysis": project.analysis_data,
        "review": project.analysis_review,
        "process_plan_status": project.process_plan_status,
        "route_review": project.route_review,
    }


@router.put(
    "/projects/{project_id}/analysis/review",
    response_model=ProjectAnalysisResponse,
)
def update_project_analysis_review(
    project_id: UUID,
    review_update: ProjectAnalysisReviewUpdate,
    db: Session = Depends(get_db),
    reviewer: str = Depends(get_current_user),
):
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.analysis_data:
        raise HTTPException(status_code=409, detail="Drawing analysis is not ready for review")

    targets = get_review_targets(project.analysis_data)
    submitted_ids = [decision.target_id for decision in review_update.decisions]
    if len(set(submitted_ids)) != len(submitted_ids):
        raise HTTPException(status_code=422, detail="Each review target may only be submitted once")
    unknown_ids = set(submitted_ids) - targets.keys()
    if unknown_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown or stale review targets: {', '.join(sorted(unknown_ids))}",
        )
    if review_update.status == "approved" and set(submitted_ids) != targets.keys():
        missing_ids = sorted(targets.keys() - set(submitted_ids))
        raise HTTPException(
            status_code=422,
            detail=f"All extracted callouts must be reviewed before approval: {', '.join(missing_ids)}",
        )

    review = ProjectAnalysisReview(
        status=review_update.status,
        reviewer=reviewer,
        updated_at=datetime.now(timezone.utc),
        decisions=review_update.decisions,
    )
    project.analysis_review = review.model_dump(mode="json")
    project.status = "analysis_approved" if review_update.status == "approved" else "analysis_ready"
    db.commit()
    db.refresh(project)
    return {
        "project_id": str(project.id),
        "status": project.status,
        "analysis": project.analysis_data,
        "review": project.analysis_review,
        "process_plan_status": project.process_plan_status,
        "route_review": project.route_review,
    }


@router.post(
    "/projects/{project_id}/routes",
    response_model=list[OperationSchema],
)
def generate_project_routes(project_id: UUID, db: Session = Depends(get_db)):
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        operations = ManufacturingRouteService.generate(db, project)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    project.status = "routing"
    db.commit()
    return operations


@router.put("/projects/{project_id}/routes/review")
def review_project_routes(
    project_id: UUID,
    review_update: ProcessPlanReviewUpdate,
    db: Session = Depends(get_db),
    reviewer: str = Depends(get_current_user),
):
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    operations = db.query(ManufacturingOperation).filter(
        ManufacturingOperation.project_id == project_id
    ).all()
    if project.process_plan_status not in {"generated", "changes_requested"} or not operations:
        raise HTTPException(status_code=409, detail="Manufacturing routes are not ready for review")

    submitted_ids = [operation.operation_id for operation in review_update.operations]
    existing_ids = {operation.id for operation in operations}
    if len(set(submitted_ids)) != len(submitted_ids) or set(submitted_ids) != existing_ids:
        raise HTTPException(
            status_code=422,
            detail="Route review must include each current operation exactly once",
        )
    sequence_orders = [operation.sequence_order for operation in review_update.operations]
    if len(set(sequence_orders)) != len(sequence_orders):
        raise HTTPException(status_code=422, detail="Operation sequence numbers must be unique")

    operations_by_id = {operation.id: operation for operation in operations}
    for reviewed_operation in review_update.operations:
        operation = operations_by_id[reviewed_operation.operation_id]
        operation.operation_name = reviewed_operation.operation_name
        operation.sequence_order = reviewed_operation.sequence_order
        operation.estimated_time_minutes = reviewed_operation.estimated_time_minutes
        operation.estimated_cost = reviewed_operation.estimated_cost
        operation.machine_type = reviewed_operation.machine_type

    project.process_plan_status = review_update.status
    project.status = "costed" if review_update.status == "approved" else "routing"
    project.route_review = {
        "status": review_update.status,
        "reviewer": reviewer,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "comment": review_update.comment,
    }
    db.commit()
    db.refresh(project)
    return {
        "project_id": str(project.id),
        "process_plan_status": project.process_plan_status,
        "route_review": project.route_review,
        "operations": operations,
    }

@router.get("/projects/{project_id}/features", response_model=list[FeatureSchema])
def get_project_features(project_id: UUID, db: Session = Depends(get_db)):
    features = db.query(ManufacturingFeature).filter(ManufacturingFeature.project_id == project_id).all()
    return features

@router.get("/projects/{project_id}/operations", response_model=list[OperationSchema])
def get_project_operations(project_id: UUID, db: Session = Depends(get_db)):
    operations = db.query(ManufacturingOperation).filter(ManufacturingOperation.project_id == project_id).all()
    return operations

@router.post("/projects/{project_id}/quote", response_model=QuoteResponse)
def create_project_quote(project_id: UUID, db: Session = Depends(get_db)):
    try:
        quote = CostingService.create_project_quote(db, project_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _quote_response(quote)


@router.get("/projects/{project_id}/quote", response_model=QuoteResponse)
def get_project_quote(project_id: UUID, db: Session = Depends(get_db)):
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    quote = db.query(Quote).filter(
        Quote.project_id == project_id
    ).order_by(Quote.created_at.desc()).first()
    if quote is None:
        raise HTTPException(status_code=404, detail="No quote has been generated")
    return _quote_response(quote)

@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    customer = db.get(CustomerModel, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check if customer has linked RFQs/Projects
    rfqs = db.query(RFQModel).filter(RFQModel.customer_id == customer_id).all()
    if rfqs:
        raise HTTPException(status_code=409, detail="Cannot delete customer with active RFQs/Projects")

    db.delete(customer)
    db.commit()
    return None

@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    project = db.get(ProjectModel, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Cascade deletion of related entities (files, operations, etc.)
    # SQLAlchemy relationships should handle this if cascade="all, delete-orphan" is set,
    # otherwise we handle it manually here.
    db.delete(project)
    db.commit()
    return None
