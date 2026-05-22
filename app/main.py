import logging
from pathlib import Path
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect as sa_inspect
from app.core.database import engine, Base
import app.models  # noqa: F401 — registers all ORM models with Base before create_all
from app.api.routes import ussd, storage, forecasts, dashboard, recommendations

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_log = logging.getLogger(__name__)

_APP_TABLES = {
    'storage_locations', 'wfp_markets', 'wfp_prices',
    'ghana_exchange_rates', 'fao_producer_prices',
    'recommendations', 'price_forecasts',
}

_insp = sa_inspect(engine)
_db_is_fresh = not any(_insp.has_table(t) for t in _APP_TABLES)

with engine.connect() as _conn:
    _current_revision = MigrationContext.configure(_conn).get_current_revision()

if _current_revision is None and not _db_is_fresh:
    _log.error(
        "Database has application tables but no alembic_version entry. "
        "Run 'alembic upgrade head' before starting the app."
    )
    raise RuntimeError(
        "Refusing to start: pre-Alembic database state detected. "
        "Run 'alembic upgrade head' before starting the app."
    )

Base.metadata.create_all(bind=engine)

if _current_revision is None and _db_is_fresh:
    command.stamp(Config(str(_ALEMBIC_INI)), "head")

app = FastAPI(
    title="PostHarvest IQ API",
    description="Sell-or-Store Decision Intelligence for Ghanaian Smallholder Farmers",
    version="1.0.0"
)

app.include_router(ussd.router,            prefix="/ussd",            tags=["USSD"])
app.include_router(storage.router,         prefix="/storage",         tags=["Storage"])
app.include_router(forecasts.router,       prefix="/forecasts",       tags=["Forecasts"])
app.include_router(dashboard.router,       prefix="/dashboard",       tags=["Dashboard"])
app.include_router(recommendations.router, prefix="/recommendations",  tags=["Recommendations"])

@app.get("/")
def root():
    return {"status": "PostHarvest IQ API running", "version": "1.0.0"}