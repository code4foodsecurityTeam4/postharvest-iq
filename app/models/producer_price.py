from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class ProducerPrice(Base):
    __tablename__ = "fao_producer_prices"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    iso3         = Column(String(10))
    area         = Column(String(100))
    item         = Column(String(100))
    element      = Column(String(100))
    year         = Column(Integer)
    months       = Column(String(50))
    unit         = Column(String(50))
    value        = Column(Float)
    flag         = Column(String(10))