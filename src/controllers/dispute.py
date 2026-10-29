import sqlite3
from typing import List
from schemas.dispute import ComplaintCreateSchema, AuthenticatedUserSchema, ComplaintValidationResponse
from models.dispute import ComplaintModel
from services.dispute import DisputeWorkflowService

class DisputeController:
    @staticmethod
    def create_complaint(
        db: sqlite3.Connection, 
        payload: ComplaintCreateSchema, 
        user: AuthenticatedUserSchema, 
        request_id: str
    ) -> ComplaintModel:
        """Coordinates the creation and external registration of a complaint."""
        return DisputeWorkflowService(db).file_new_complaint(payload, user, request_id)

    @staticmethod
    def validate_complaint(
        payload: ComplaintCreateSchema, 
        user: AuthenticatedUserSchema
    ) -> ComplaintValidationResponse:
        """Validates complaint data without creating a complaint or audit record."""
        DisputeWorkflowService.validate_complaint_payload(payload)
        return ComplaintValidationResponse(
            valid=True,
            message="Complaint data is valid.",
        )

    @staticmethod
    def get_complaint(
        db: sqlite3.Connection, 
        complaint_id: str, 
        user: AuthenticatedUserSchema
    ) -> ComplaintModel:
        """Coordinates fetching a complaint while verifying tenant bank ownership."""
        return DisputeWorkflowService(db).fetch_permitted_complaint(complaint_id, user)

    @staticmethod
    def list_complaints(
        db: sqlite3.Connection, 
        user: AuthenticatedUserSchema
    ) -> List[ComplaintModel]:
        """Coordinates fetching all complaints belonging exclusively to the operator's bank."""
        return DisputeWorkflowService(db).browse_bank_ledger(user)
