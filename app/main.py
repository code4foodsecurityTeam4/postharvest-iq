from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.routes import ussd, storage, forecasts, dashboard

Base.metadata.create_all(bind=engine)

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