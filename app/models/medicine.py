from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Medicine(Base):
    __tablename__ = "medicine"

    med_his_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    name20 = Column(String(20), nullable=True)
    specs = Column(String, nullable=True)
    factory_name = Column(String, nullable=True)
    tray_no = Column(Integer, unique=True, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tray = relationship("Tray", back_populates="medicine", uselist=False)
