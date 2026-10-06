from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Tray(Base):
    __tablename__ = "tray"

    tray_no = Column(Integer, primary_key=True)
    med_his_id = Column(String, ForeignKey("medicine.med_his_id"), nullable=True)
    quantity = Column(Integer, nullable=True)
    status = Column(Integer, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    medicine = relationship("Medicine", back_populates="tray")
