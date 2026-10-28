from pydantic import BaseModel, Field
from typing import Optional

class ComplaintCreateSchema(BaseModel):
    transfer_reference: str = Field(..., min_length=5)
    amount: str = Field(...)
    currency: str = Field("RWF", max_length=3)
    category: str = Field(..., description="debited_not_credited, wrong_recipient, duplicate, scam")
    description: Optional[str] = ""
    evidence: Optional[str] = None

class ComplaintResponseSchema(BaseModel):
    id: str
    bank: str
    operator_username: str
    transfer_reference: str
    amount: str
    currency: str
    category: str
    description: Optional[str]
    evidence: Optional[str]
    registration_status: str
    hub_claim_id: Optional[str]
    hub_error_message: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class ComplaintSuccessEnvelope(BaseModel):
    complaint_id: str
    registration_status: str
    hub_claim_id: Optional[str] = None
    request_id: str

class AuthenticatedUserSchema(BaseModel):
    username: str
    bank: str
    
class LoginRequestSchema(BaseModel):
    username: str
    password: str

class LoginResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    bank: str

