from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class DispenseLog(Base):
    __tablename__ = "dispense_log"

    id = Column(Integer, primary_key=True)
    prescription_detail_id = Column(Integer, ForeignKey("prescription_detail.id"), nullable=True)
    tray_no = Column(Integer, nullable=False)
    requested_quantity = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    prescription_detail = relationship("PrescriptionDetail", back_populates="dispense_logs")
