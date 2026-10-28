from typing import Optional

class ComplaintModel:
    def __init__(
        self, id: str, bank: str, operator_username: str, transfer_reference: str,
        amount: str, currency: str, category: str, description: Optional[str],
        evidence: Optional[str], registration_status: str, hub_claim_id: Optional[str],
        hub_error_message: Optional[str], created_at: str
    ):
        self.id = id
        self.bank = bank
        self.operator_username = operator_username
        self.transfer_reference = transfer_reference
        self.amount = amount
        self.currency = currency
        self.category = category
        self.description = description
        self.evidence = evidence
        self.registration_status = registration_status
        self.hub_claim_id = hub_claim_id
        self.hub_error_message = hub_error_message
        self.created_at = created_at

class AuditLogModel:
    def __init__(self, id: str, request_id: str, operator_username: str, bank: str, action: str, target_id: Optional[str], timestamp: str):
        self.id = id
        self.request_id = request_id
        self.operator_username = operator_username
        self.bank = bank
        self.action = action
        self.target_id = target_id
        self.timestamp = timestamp
