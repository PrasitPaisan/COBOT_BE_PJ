from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class PrescriptionDetail(Base):
    __tablename__ = "prescription_detail"

    id = Column(Integer, primary_key=True)
    prescription_id = Column(Integer, ForeignKey("prescription.id"), nullable=False)
    med_his_id = Column(String, nullable=False)
    requested_quantity = Column(Integer, nullable=False)
    tray_no = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="pending")
    message = Column(Text, nullable=True)
    dispensed_at = Column(DateTime(timezone=True), nullable=True)

    prescription = relationship("Prescription", back_populates="details")
    dispense_logs = relationship("DispenseLog", back_populates="prescription_detail")
