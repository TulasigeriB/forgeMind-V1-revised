from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.models.rfq import RFQ
from app.models.project import Project
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.rfq import RFQCreate
from app.schemas.project import ProjectCreate
from typing import List
from uuid import UUID

class ProjectService:
    class CustomerAlreadyExistsError(Exception):
        pass

    @staticmethod
    def get_customer_by_email(db: Session, email: str):
        normalized_email = email.strip().lower()
        return db.query(Customer).filter(
            func.lower(Customer.contact_email) == normalized_email
        ).first()

    @staticmethod
    def get_all_customers(db: Session) -> List[Customer]:
        return db.query(Customer).order_by(Customer.name).all()

    @staticmethod
    def create_customer(db: Session, customer: CustomerCreate):
        normalized_email = str(customer.contact_email).strip().lower()
        if ProjectService.get_customer_by_email(db, normalized_email):
            raise ProjectService.CustomerAlreadyExistsError(normalized_email)

        values = customer.model_dump()
        values["contact_email"] = normalized_email
        db_customer = Customer(**values)
        db.add(db_customer)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ProjectService.CustomerAlreadyExistsError(normalized_email) from error
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def update_customer(db: Session, customer_id: UUID, customer: CustomerUpdate):
        db_customer = db.get(Customer, customer_id)
        if db_customer is None:
            return None

        values = customer.model_dump(exclude_unset=True)
        if "contact_email" in values:
            normalized_email = str(values["contact_email"]).strip().lower()
            existing_customer = ProjectService.get_customer_by_email(db, normalized_email)
            if existing_customer is not None and existing_customer.id != customer_id:
                raise ProjectService.CustomerAlreadyExistsError(normalized_email)
            values["contact_email"] = normalized_email

        for field, value in values.items():
            setattr(db_customer, field, value)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ProjectService.CustomerAlreadyExistsError(values.get("contact_email", "")) from error
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def create_rfq(db: Session, rfq: RFQCreate):
        db_rfq = RFQ(**rfq.model_dump())
        db.add(db_rfq)
        db.commit()
        db.refresh(db_rfq)
        return db_rfq

    @staticmethod
    def create_project(db: Session, project: ProjectCreate):
        db_project = Project(**project.model_dump())
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project

    @staticmethod
    def get_all_projects(db: Session) -> List[Project]:
        return db.query(Project).all()

    @staticmethod
    def get_project(db: Session, project_id: UUID):
        return db.query(Project).filter(Project.id == project_id).first()
