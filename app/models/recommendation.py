from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id              = Column(Integer, primary_key=True, index=True)
    session_id      = Column(String(100))
    phone_number    = Column(String(20))
    language        = Column(String(10))
    crop            = Column(String(50))
    quantity_bags   = Column(Integer)
    district        = Column(String(100))
    current_price   = Column(Float)
    forecast_price  = Column(Float)
    decision        = Column(String(20))
    net_return      = Column(Float)
    storage_id      = Column(Integer)
    created_at      = Column(DateTime, default=func.now())