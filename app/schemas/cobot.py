from pydantic import BaseModel


class COBOTTask(BaseModel):
    TrayNo: int
    Quantity: int
