from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class ProducerPrice(Base):
    __tablename__ = "fao_producer_prices"

    iso3         = Column("ISO3", String(10), primary_key=True)
    area         = Column("Area", String(100), primary_key=True)
    item         = Column("Item", String(100), primary_key=True)
    element      = Column("Element", String(100), primary_key=True)
    year         = Column("Year", Integer, primary_key=True)
    months       = Column("Months", String(50), primary_key=True)
    unit         = Column("Unit", String(50))
    value        = Column("Value", Float)
    flag         = Column("Flag", String(10))