from sqlalchemy import Column, Integer, String, Float, Date
from app.core.database import Base

class WFPPrice(Base):
    __tablename__ = "wfp_prices"

    id           = Column(Integer,     primary_key=True, autoincrement=True)
    date         = Column(Date,        nullable=False)
    admin1       = Column(String(100), nullable=False)
    admin2       = Column(String(100), nullable=False)
    market       = Column(String(200), nullable=False)
    market_id    = Column(Integer,     nullable=False)
    latitude     = Column(Float)
    longitude    = Column(Float)
    category     = Column(String(100))
    commodity    = Column(String(100), nullable=False)
    commodity_id = Column(Integer)
    unit         = Column(String(50))
    priceflag    = Column(String(20))
    pricetype    = Column(String(20),  nullable=False)
    currency     = Column(String(10))
    price        = Column(Float,       nullable=False)
    usdprice     = Column(Float)
