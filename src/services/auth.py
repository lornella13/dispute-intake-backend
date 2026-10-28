from typing import Optional
from schemas.dispute import AuthenticatedUserSchema, LoginRequestSchema, LoginResponseSchema
from core.error import UnauthenticatedError, PermissionDeniedError

MOCK_TOKENS = {
    "op_green_token": {"username": "aline_green", "bank": "Greenbank"},
    "op_blue_token": {"username": "brian_blue", "bank": "Bluemobile"},
}

class IdentityService:
    @staticmethod
    def verify_security_session(authorization: Optional[str]) -> AuthenticatedUserSchema:
        """Validates incoming bearer authorization headers and signatures."""
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthenticatedError(
                message="Invalid token parameters.",
                error_code="UNAUTHENTICATED",
            )
        try:
            scheme, token = authorization.split(" ", 1)
        except ValueError:
            raise UnauthenticatedError(
                message="Invalid token parameters.",
                error_code="UNAUTHENTICATED",
            )
        if scheme.lower() != "bearer" or not token.strip():
            raise UnauthenticatedError(
                message="Invalid token parameters.",
                error_code="UNAUTHENTICATED",
            )
            
        token = token.strip()
        if token not in MOCK_TOKENS:
            raise PermissionDeniedError(
                message="Session signature invalid or expired.",
                error_code="PERMISSION_DENIED",
            )
        return AuthenticatedUserSchema(**MOCK_TOKENS[token])

    @staticmethod
    def authenticate_operator(payload: LoginRequestSchema) -> dict:
        """Validates operator identity secrets and returns session credentials."""
        if payload.username == "aline_green" and payload.password == "green123":
            return {
                "access_token": "op_green_token",
                "token_type": "bearer",
                "bank": "Greenbank",
            }
        elif payload.username == "brian_blue" and payload.password == "blue123":
            return {
                "access_token": "op_blue_token",
                "token_type": "bearer",
                "bank": "Bluemobile",
            }
        else:
            raise UnauthenticatedError(
                message="Authentication failed: Invalid operator username or password secret sequence.",
                error_code="AUTH_FAILED",
            )
