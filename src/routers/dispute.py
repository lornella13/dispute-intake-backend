import uuid
import sqlite3
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Request
from database import get_db_connection

from schemas.dispute import (
    ComplaintCreateSchema,
    ComplaintResponseSchema,
    ComplaintSuccessEnvelope,
    AuthenticatedUserSchema,
    LoginRequestSchema,
    LoginResponseSchema,
)

from controllers.dispute import DisputeController
from services.auth import IdentityService

router = APIRouter(tags=["Complaints Handling Operations"])


def resolve_security_session(authorization: Optional[str] = Header(None)) -> AuthenticatedUserSchema:
    
    return IdentityService.verify_security_session(authorization)


def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.post("/complaints", response_model=ComplaintSuccessEnvelope)
def register_complaint(
    request: Request,
    payload: ComplaintCreateSchema,
    user: AuthenticatedUserSchema = Depends(resolve_security_session),
    db: sqlite3.Connection = Depends(get_db),
):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    model = DisputeController.create_complaint(db, payload, user, req_id)
    return ComplaintSuccessEnvelope(
        complaint_id=model.id,
        registration_status=model.registration_status,
        hub_claim_id=model.hub_claim_id,
        request_id=req_id,
    )


@router.get("/complaints", response_model=List[ComplaintResponseSchema])
def get_complaints_queue(
    user: AuthenticatedUserSchema = Depends(resolve_security_session),
    db: sqlite3.Connection = Depends(get_db),
):
    return DisputeController.list_complaints(db, user)


@router.get("/complaints/{id}", response_model=ComplaintResponseSchema)
def get_complaint_by_id(
    id: str,
    user: AuthenticatedUserSchema = Depends(resolve_security_session),
    db: sqlite3.Connection = Depends(get_db),
):
    return DisputeController.get_complaint(db, id, user)


@router.get("/health", tags=["System Utility"])
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "environment": "sandbox-development",
    }


@router.post("/auth/login", response_model=LoginResponseSchema, tags=["Identity Management"])
def login_operator(payload: LoginRequestSchema):
    
    return IdentityService.authenticate_operator(payload)
