from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class PriceForecast(Base):
    __tablename__ = "price_forecasts"

    id            = Column(Integer, primary_key=True, index=True)
    crop          = Column(String(50), nullable=False)
    district      = Column(String(100), nullable=False)
    forecast_date = Column(Date, nullable=False)
    price_low     = Column(Float)
    price_mid     = Column(Float)
    price_high    = Column(Float)
    created_at    = Column(DateTime, default=func.now())