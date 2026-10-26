from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import our models here
import sys
from pathlib import Path

# The application package lives under ``backend`` while Alembic is run from
# the repository root. Add that directory explicitly so all imports use the
# same ``app`` package namespace as the application itself.
backend_dir = Path(__file__).resolve().parents[1] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.session import Base  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
from app.models.customer import Customer
from app.models.rfq import RFQ
from app.models.project import Project
from app.models.engineering_file import EngineeringFile
from app.models.feature import ManufacturingFeature, CostTemplate
from app.models.operation import ManufacturingOperation
from app.models.quote import Quote

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the magic line that tells Alembic what tables to create
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
