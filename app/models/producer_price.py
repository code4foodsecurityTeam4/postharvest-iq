from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class ProducerPrice(Base):
    __tablename__ = "fao_producer_prices"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    iso3    = Column(String(10),  nullable=False)
    area    = Column(String(100), nullable=False)
    item    = Column(String(100), nullable=False)
    element = Column(String(100), nullable=False)
    year    = Column(Integer,     nullable=False)
    months  = Column(String(50),  nullable=False)
    unit    = Column(String(50))
    value   = Column(Float,       nullable=False)
    flag    = Column(String(10))
