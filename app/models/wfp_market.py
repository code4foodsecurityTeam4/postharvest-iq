from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class WFPMarket(Base):
    __tablename__ = "wfp_markets"

    market_id   = Column(Integer,     primary_key=True)
    market      = Column(String(200), nullable=False)
    countryiso3 = Column(String(10),  nullable=False)
    admin1      = Column(String(100), nullable=False)
    admin2      = Column(String(100), nullable=False)
    latitude    = Column(Float,       nullable=False)
    longitude   = Column(Float,       nullable=False)
