from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class ExchangeRate(Base):
    __tablename__ = "ghana_exchange_rates"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    iso3         = Column(String(10))
    area         = Column(String(100))
    year         = Column(Integer)
    months       = Column(String(50))
    unit         = Column(String(50))
    value        = Column(Float)
    flag         = Column(String(10))