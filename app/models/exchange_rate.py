from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class ExchangeRate(Base):
    __tablename__ = "ghana_exchange_rates"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    iso3         = Column("Iso3", String(10))
    area         = Column("Area", String(100))
    year         = Column("Year", Integer)
    months       = Column("Months", String(50))
    start_date   = Column("StartDate", String(50))
    unit         = Column("Unit", String(50))
    value        = Column("Value", Float)
    flag         = Column("Flag", String(10))