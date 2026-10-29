import hashlib
import hmac
import json
import os
import time
import base64
from typing import Optional
from schemas.dispute import AuthenticatedUserSchema, LoginRequestSchema, LoginResponseSchema
from core.error import UnauthenticatedError, PermissionDeniedError


# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

def _load_operators() -> dict:
    """Load demo operator credentials from environment variables.

    Expected format (per operator):
      OP_GREEN_USERNAME=aline_green
      OP_GREEN_PASSWORD_HASH=<pbkdf2-hmac-sha256-hash>$<base64-salt>
      OP_GREEN_BANK=Greenbank

    Returns a dict mapping username -> {password_hash, bank}.
    Raises RuntimeError if required configuration is missing (fail-safe).
    """
    operators = {}
    # Support both named operators (OP_GREEN_*, OP_BLUE_*) and a generic
    # indexed scheme (OP_1_USERNAME, OP_1_PASSWORD_HASH, OP_1_BANK, ...).
    prefixes = []
    for i in range(1, 10):
        prefixes.append(f"OP_{i}")
    prefixes.extend(["OP_GREEN", "OP_BLUE"])

    seen_usernames = set()
    for prefix in prefixes:
        username = os.getenv(f"{prefix}_USERNAME")
        password_hash = os.getenv(f"{prefix}_PASSWORD_HASH")
        bank = os.getenv(f"{prefix}_BANK")
        if username and password_hash and bank:
            if username in seen_usernames:
                continue
            seen_usernames.add(username)
            operators[username] = {
                "password_hash": password_hash,
                "bank": bank,
            }

    if not operators:
        raise RuntimeError(
            "No operator credentials configured. "
            "Set OP_*_USERNAME, OP_*_PASSWORD_HASH, OP_*_BANK environment variables "
            "or copy .env.example to .env and fill in the values."
        )

    return operators


def _load_jwt_config() -> dict:
    """Load JWT signing configuration from environment variables.

    Raises RuntimeError if JWT_SECRET_KEY is missing (fail-safe).
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. "
            "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    if algorithm != "HS256":
        raise RuntimeError(f"Unsupported JWT algorithm: {algorithm}")
    try:
        expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except ValueError:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer")

    return {
        "secret_key": secret_key,
        "algorithm": algorithm,
        "expire_minutes": expire_minutes,
    }


# Load configuration at import time. Fail safely if required config is missing.
try:
    OPERATORS = _load_operators()
    JWT_CONFIG = _load_jwt_config()
except RuntimeError as _exc:
    # Defer the error to first use so that module import doesn't crash
    # unrelated tooling (e.g. linting). The service will raise on use.
    OPERATORS = None
    JWT_CONFIG = None
    _CONFIG_ERROR = _exc
else:
    _CONFIG_ERROR = None


def _ensure_config():
    if _CONFIG_ERROR is not None:
        raise RuntimeError(str(_CONFIG_ERROR))


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256, standard library only)
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256.

    Returns a string in the format: <base64-hash>$<base64-salt>
    """
    if salt is None:
        salt = base64.b64encode(os.urandom(16)).decode("utf-8")
    pwdhash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        base64.b64decode(salt),
        100000,
    )
    return base64.b64encode(pwdhash).decode("utf-8") + "$" + salt


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored PBKDF2 hash (timing-safe)."""
    try:
        pwdhash_b64, salt = stored.split("$", 1)
    except ValueError:
        return False
    try:
        pwdhash = base64.b64decode(pwdhash_b64)
        salt_bytes = base64.b64decode(salt)
    except Exception:
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        100000,
    )
    return hmac.compare_digest(computed, pwdhash)


# ---------------------------------------------------------------------------
# Signed token mechanism (HMAC-SHA256, standard library only)
# Token format: <header>.<payload>.<signature>  (base64url, no padding)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_access_token(data: dict, secret_key: str, expires_delta_minutes: int) -> str:
    """Create a signed access token with expiration.

    Payload claims: sub (username), bank, exp, iat
    """
    to_encode = data.copy()
    now = int(time.time())
    expire = now + expires_delta_minutes * 60
    to_encode.update({"exp": expire, "iat": now})

    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    payload = _b64url_encode(json.dumps(to_encode).encode("utf-8"))
    signing_input = f"{header}.{payload}".encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header}.{payload}.{signature_b64}"


def verify_access_token(token: str, secret_key: str) -> dict:
    """Verify token signature, expiration, and required claims.

    Returns the decoded payload dict.
    Raises UnauthenticatedError or PermissionDeniedError on failure.
    """
    _ensure_config()

    parts = token.split(".")
    if len(parts) != 3:
        raise UnauthenticatedError(
            message="Invalid token parameters.",
            error_code="UNAUTHENTICATED",
        )

    header_b64, payload_b64, signature_b64 = parts

    # Constant-time signature verification
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(
        secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)
    if not hmac.compare_digest(expected_sig_b64, signature_b64):
        raise PermissionDeniedError(
            message="Session signature invalid or expired.",
            error_code="PERMISSION_DENIED",
        )

    # Decode payload
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise UnauthenticatedError(
            message="Invalid token parameters.",
            error_code="UNAUTHENTICATED",
        )

    # Validate required claims
    if "sub" not in payload or "bank" not in payload:
        raise UnauthenticatedError(
            message="Invalid token parameters.",
            error_code="UNAUTHENTICATED",
        )

    # Validate expiration
    exp = payload.get("exp")
    if exp is None:
        raise UnauthenticatedError(
            message="Invalid token parameters.",
            error_code="UNAUTHENTICATED",
        )
    if time.time() > exp:
        raise PermissionDeniedError(
            message="Session signature invalid or expired.",
            error_code="PERMISSION_DENIED",
        )

    return payload


# ---------------------------------------------------------------------------
# IdentityService
# ---------------------------------------------------------------------------

class IdentityService:
    @staticmethod
    def verify_security_session(authorization: Optional[str]) -> AuthenticatedUserSchema:
        """Validates incoming bearer authorization headers and signed JWT tokens."""
        _ensure_config()

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
        payload = verify_access_token(token, JWT_CONFIG["secret_key"])

        return AuthenticatedUserSchema(
            username=payload["sub"],
            bank=payload["bank"],
        )

    @staticmethod
    def authenticate_operator(payload: LoginRequestSchema) -> dict:
        """Validates operator identity secrets and returns signed session credentials."""
        _ensure_config()

        operator = OPERATORS.get(payload.username)
        if operator is None:
            raise UnauthenticatedError(
                message="Authentication failed: Invalid operator username or password secret sequence.",
                error_code="AUTH_FAILED",
            )

        if not _verify_password(payload.password, operator["password_hash"]):
            raise UnauthenticatedError(
                message="Authentication failed: Invalid operator username or password secret sequence.",
                error_code="AUTH_FAILED",
            )

        access_token = create_access_token(
            data={"sub": payload.username, "bank": operator["bank"]},
            secret_key=JWT_CONFIG["secret_key"],
            expires_delta_minutes=JWT_CONFIG["expire_minutes"],
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "bank": operator["bank"],
        }
