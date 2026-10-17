"""Single declarative base shared by all SQLAlchemy models."""
from sqlalchemy.orm import DeclarativeBase


class BaseModel(DeclarativeBase):
    pass
