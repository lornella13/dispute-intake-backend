import uuid
import datetime
import sqlite3
from typing import List
from models.dispute import ComplaintModel, AuditLogModel
from schemas.dispute import ComplaintCreateSchema, AuthenticatedUserSchema
from repositories.dispute import DisputeRepository, AuditRepository
from core.error import ValidationBusinessError, NotFoundError

class DisputeWorkflowService:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.dispute_repo = DisputeRepository()
        self.audit_repo = AuditRepository()

    @staticmethod
    def mock_external_hub_call(transfer_ref: str) -> dict:
        if transfer_ref.endswith("999"):
            return {"status": "REJECTED", "claim_id": None, "message": "Scheme violation: Exceeded bounds."}
        return {"status": "REGISTERED", "claim_id": f"CLM-{uuid.uuid4().hex[:8].upper()}", "message": "Success"}

    def file_new_complaint(self, payload: ComplaintCreateSchema, user: AuthenticatedUserSchema, request_id: str) -> ComplaintModel:
        
        if payload.category in ["wrong_recipient", "scam"] and not payload.evidence:
            raise ValidationBusinessError(
                message=f"Category '{payload.category}' requires evidence files.",
                error_code="VALIDATION_FAILED"
            )

        hub_response = self.mock_external_hub_call(payload.transfer_reference)
        complaint_id = f"CMP-{uuid.uuid4().hex[:6].upper()}"
        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        complaint_model = ComplaintModel(
            id=complaint_id, 
            bank=user.bank, 
            operator_username=user.username,
            transfer_reference=payload.transfer_reference, 
            amount=payload.amount,
            currency=payload.currency, 
            category=payload.category, 
            description=payload.description,
            evidence=payload.evidence, 
            registration_status=hub_response["status"],
            hub_claim_id=hub_response["claim_id"],
            hub_error_message=hub_response["message"] if hub_response["status"] == "REJECTED" else None,
            created_at=current_time
        )

        
        self.dispute_repo.persist_complaint(self.db, complaint_model)
        
        self.audit_repo.log_event(self.db, AuditLogModel(
            id=str(uuid.uuid4()), 
            request_id=request_id, 
            operator_username=user.username,
            bank=user.bank, 
            action="CREATE_COMPLAINT", 
            target_id=complaint_id,
            timestamp=current_time
        ))
        return complaint_model

    def fetch_permitted_complaint(self, complaint_id: str, user: AuthenticatedUserSchema) -> ComplaintModel:
        complaint = self.dispute_repo.get_by_id(self.db, complaint_id)
        
        if not complaint or complaint.bank != user.bank:
            raise NotFoundError(
                message="Complaint index reference not found",
                error_code="COMPLAINT_NOT_FOUND"
            )
        return complaint

    def browse_bank_ledger(self, user: AuthenticatedUserSchema) -> List[ComplaintModel]:
        return self.dispute_repo.list_by_bank(self.db, user.bank)
