from enum import Enum

class DisputeCategory(str, Enum):
    DEBITED_NOT_CREDITED = "debited_not_credited"
    WRONG_RECIPIENT = "wrong_recipient"
    DUPLICATE = "duplicate"
    SCAM = "scam"

class RegistrationStatus(str, Enum):
    DRAFT = "Draft"
    PENDING = "Pending Registration"
    REGISTERED = "REGISTERED"
    REJECTED = "REJECTED"
