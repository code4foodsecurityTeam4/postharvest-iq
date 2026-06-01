from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class ExchangeRate(Base):
    __tablename__ = "ghana_exchange_rates"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    iso3     = Column(String(10),  nullable=False)
    area     = Column(String(100), nullable=False)
    year     = Column(Integer,     nullable=False)
    months   = Column(String(50),  nullable=False)
    element  = Column(String(100), nullable=False)
    value    = Column(Float,       nullable=False)
    flag     = Column(String(10))
