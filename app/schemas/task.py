from pydantic import BaseModel


class TaskLookupRequest(BaseModel):
    TaskNo: str
