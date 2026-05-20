from logging.config import fileConfig

from alembic import context

from app.core.database import engine, Base
import app.models  # noqa: F401 — side-effect import: registers all ORM models with Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables managed outside Alembic (loaded via load_data.py with if_exists='replace').
# Exclude them so autogenerate never flags them as missing.
EXCLUDE_TABLES = {'language_admin1', 'language_admin2'}


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ARG001
    """Return False for tables intentionally managed outside Alembic."""
    del obj, reflected, compare_to  # required by Alembic callback signature
    if type_ == 'table' and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
