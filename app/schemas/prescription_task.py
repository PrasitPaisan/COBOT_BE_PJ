from typing import List, Optional

from pydantic import BaseModel


class MedicineItem(BaseModel):
    MedHisId: str
    MedName: str
    MedSpecs: Optional[str] = None
    MedFactoryName: Optional[str] = None
    MedNumber: int
    MedUnit: Optional[str] = None
    MedHint: Optional[str] = None


class PrescriptionTask(BaseModel):
    TaskNo: str
    PreHisId: str
    PreId: int
    BasketId: int
    SplitId: int
    PatId: str
    PatName: str
    PatAge: int
    PatSex: str
    MedicineList: List[MedicineItem]
