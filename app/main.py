from fastapi import FastAPI
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from app.core.database import engine, Base
import app.models  # noqa: F401 — registers all ORM models with Base before create_all
from app.api.routes import ussd, storage, forecasts, dashboard

Base.metadata.create_all(bind=engine)

# On a fresh DB (no alembic_version row), stamp head so future migrations apply cleanly.
with engine.connect() as _conn:
    if MigrationContext.configure(_conn).get_current_revision() is None:
        command.stamp(Config("alembic.ini"), "head")

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