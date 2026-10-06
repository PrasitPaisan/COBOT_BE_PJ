from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Prescription(Base):
    __tablename__ = "prescription"

    id = Column(Integer, primary_key=True)
    task_no = Column(String, unique=True, nullable=True)
    pre_his_id = Column(String, nullable=True)
    pre_id = Column(Integer, nullable=True)
    basket_id = Column(Integer, nullable=True)
    split_id = Column(Integer, nullable=True)
    pat_id = Column(String, nullable=True)
    pat_name = Column(String, nullable=True)
    pat_age = Column(Integer, nullable=True)
    pat_sex = Column(String(1), nullable=True)
    status = Column(String, nullable=False, default="pending")
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    details = relationship("PrescriptionDetail", back_populates="prescription")
