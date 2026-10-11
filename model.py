from datetime import datetime

from pydantic import BaseModel

class EmailStructure(BaseModel):
    message_id: str
    sender: str
    subject: str
    date: datetime
    body: str

class JobApplication(BaseModel):
    emailID: str = "noreply@microsoft.com"
    company: str = "microsoft"
    status: str = "Rejected"