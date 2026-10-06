from typing import Optional

from pydantic import BaseModel


class MedicineDictionary(BaseModel):
    MedId: str
    MedName: str
    Quantity: int
    Specs: Optional[str] = None
    FactoryName: Optional[str] = None
    TrayNo: Optional[int] = None
