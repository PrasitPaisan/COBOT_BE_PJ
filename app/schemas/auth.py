from pydantic import BaseModel


class LoginRequest(BaseModel):
    level: int  # 0=unlogin, 1=Pharmacist, 2=Engineer
