from datetime import datetime
from pydantic import BaseModel, Field

class ResumeDocModel(BaseModel):
    id: int
    hash: str
    model_hash: str = Field(..., alias="modelHash")
    filename: str
    display_name: str | None = Field(None, alias="displayName")
    upload_dt: datetime = Field(..., alias="uploadDt")

    class ConfigDict:
        from_attributes = True
        populate_by_name = True

class ResumeDocUpdate(BaseModel):
    display_name: str = Field(..., alias="displayName")
