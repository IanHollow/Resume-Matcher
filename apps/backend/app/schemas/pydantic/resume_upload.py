from pydantic import BaseModel

class ResumeUploadResponse(BaseModel):
    message: str
    request_id: str
    resume_id: str
