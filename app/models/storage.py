from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.core.database import Base

class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id                      = Column(Integer, primary_key=True, index=True)
    name                    = Column(String(200), nullable=False)
    type                    = Column(String(100)) 
    region                  = Column(String(100)) 
    district                = Column(String(100), nullable=False)
    gps_lat                 = Column(Float, nullable=False)
    gps_lng                 = Column(Float, nullable=False)
    cost_per_bag_per_month  = Column(Float)       
    min_bags                = Column(Integer)
    max_bags                = Column(Integer)
    crops_accepted          = Column(String(200))  
    contact_number          = Column(String(20))
    verified                = Column(Boolean, default=False)
    is_active               = Column(Boolean, default=True)  
    last_verified_date      = Column(DateTime, nullable=True)
    created_at              = Column(DateTime, default=func.now())