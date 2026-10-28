import sqlite3
from typing import List, Optional
from models.dispute import ComplaintModel, AuditLogModel

class DisputeRepository:
    @staticmethod
    def persist_complaint(db: sqlite3.Connection, model: ComplaintModel) -> None:
        db.execute(
            "INSERT INTO complaints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                model.id, model.bank, model.operator_username, model.transfer_reference,
                model.amount, model.currency, model.category, model.description,
                model.evidence, model.registration_status, model.hub_claim_id,
                model.hub_error_message, model.created_at
            )
        )
        db.commit()

    @staticmethod
    def get_by_id(db: sqlite3.Connection, complaint_id: str) -> Optional[ComplaintModel]:
        cursor = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
        row = cursor.fetchone()
        return ComplaintModel(**dict(row)) if row else None

    @staticmethod
    def list_by_bank(db: sqlite3.Connection, bank_name: str) -> List[ComplaintModel]:
        cursor = db.execute("SELECT * FROM complaints WHERE bank = ? ORDER BY created_at DESC", (bank_name,))
        return [ComplaintModel(**dict(row)) for row in cursor.fetchall()]

class AuditRepository:
    @staticmethod
    def log_event(db: sqlite3.Connection, model: AuditLogModel) -> None:
        db.execute(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?)",
            (model.id, model.request_id, model.operator_username, model.bank, model.action, model.target_id, model.timestamp)
        )
        db.commit()
