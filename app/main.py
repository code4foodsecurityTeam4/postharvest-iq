import logging
from pathlib import Path
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect as sa_inspect

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
from app.core.database import engine, Base
import app.models  # noqa: F401 — registers all ORM models with Base before create_all
from app.api.routes import ussd, storage, forecasts, dashboard

_log = logging.getLogger(__name__)

# Check BEFORE create_all so we can distinguish a truly empty DB from a
# pre-Alembic DB that already has tables but no alembic_version row.
_db_is_fresh = not sa_inspect(engine).has_table('storage_locations')

Base.metadata.create_all(bind=engine)

with engine.connect() as _conn:
    if MigrationContext.configure(_conn).get_current_revision() is None:
        if _db_is_fresh:
            # Truly new DB — create_all just built the full schema, stamp head
            # so future `alembic upgrade head` runs apply only new migrations.
            command.stamp(Config(str(_ALEMBIC_INI)), "head")
        else:
            # Tables exist but no alembic_version — pre-Alembic DB.
            # Stamping would silently skip pending migrations; fail loudly instead.
            _log.warning(
                "Database has application tables but no alembic_version entry. "
                "Run 'alembic upgrade head' to apply pending migrations before starting the app."
            )

app = FastAPI(
    title="PostHarvest IQ API",
    description="Sell-or-Store Decision Intelligence for Ghanaian Smallholder Farmers",
    version="1.0.0"
)

app.include_router(ussd.router,      prefix="/ussd",      tags=["USSD"])
app.include_router(storage.router,   prefix="/storage",   tags=["Storage"])
app.include_router(forecasts.router, prefix="/forecasts", tags=["Forecasts"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/")
def root():
    return {"status": "PostHarvest IQ API running", "version": "1.0.0"}