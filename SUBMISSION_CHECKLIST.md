# Submission Checklist — Aline's Task B: Dispute Intake Module

This checklist documents each requirement, how it is verified, and any
remaining limitations. Statuses: PASS / PARTIAL / FAIL / NOT VERIFIED.

## 1. Authentication & Login

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| POST /auth/login authenticates operators | PASS | `tests/test_regression.py::test_login_greenbank_valid` and `::test_login_bluemobile_valid` assert 200 with token + bank | None |
| Invalid credentials rejected | PASS | `tests/test_regression.py::test_login_invalid_credentials`, `::test_login_invalid_password`, `::test_login_unknown_user`, `::test_login_empty_password` assert 401 | None |
| Passwords hashed (not plain text) | PASS | `src/services/auth.py` uses PBKDF2-HMAC-SHA256 (100k iterations) | None |
| Credentials loaded from env, not hardcoded | PASS | `src/services/auth.py::_load_operators()` reads `OP_*_USERNAME/PASSWORD_HASH/BANK` | None |
| `.env.example` with placeholders only | PASS | `backend/.env.example` and `frontend/.env.example` contain placeholders | None |
| `.env` gitignored | PASS | `backend/.gitignore` contains `.env` | None |
| Signed tokens with expiration | PASS | `src/services/auth.py` creates HMAC-SHA256 tokens with `exp` claim (30 min default) | None |
| Token signature validated | PASS | `tests/test_regression.py::test_tampered_token_rejected` asserts 403 | None |
| Token expiry validated | PASS | `tests/test_regression.py::test_expired_token_rejected` asserts 403 | None |
| Missing token rejected | PASS | `tests/test_regression.py::test_missing_token_rejected` asserts 401 | None |
| Wrong auth scheme rejected | PASS | `tests/test_regression.py::test_wrong_scheme_rejected` asserts 401 | None |
| Fail-safe when config missing | PASS | `src/services/auth.py` raises `RuntimeError` if `JWT_SECRET_KEY` or operator config missing | None |

## 2. Complaint Creation

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| POST /complaints creates complaint | PASS | `tests/test_regression.py::test_create_valid_complaint` asserts 200 with `complaint_id` | None |
| Complaint persisted to SQLite | PASS | `src/services/dispute.py::file_new_complaint` calls `persist_complaint` + `log_event` | None |
| Audit log created on complaint | PASS | `src/services/dispute.py::file_new_complaint` calls `audit_repo.log_event` | None |
| Request ID in audit log | PASS | `src/routers/dispute.py` passes `req_id` from `SecurityTrackingMiddleware` | None |

## 3. Validation Rules

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| Transfer reference matches `^TXN-\d{6}$` | PASS | `tests/test_regression.py::test_transfer_reference_valid_format_accepted`, `::test_transfer_reference_too_short_rejected`, `::test_transfer_reference_letters_instead_of_digits_rejected`, `::test_transfer_reference_missing_prefix_rejected` | None |
| Amount is positive decimal string | PASS | `tests/test_regression.py::test_amount_positive_integer_string_accepted`, `::test_amount_decimal_string_accepted`, `::test_amount_zero_rejected`, `::test_amount_negative_rejected`, `::test_amount_malformed_rejected`, `::test_amount_empty_rejected` | None |
| Category restricted to 4 values | PASS | `tests/test_regression.py::test_valid_categories_accepted`, `::test_invalid_category_rejected` | None |
| Evidence required for wrong_recipient & scam | PASS | `tests/test_regression.py::test_wrong_recipient_without_evidence_rejected`, `::test_scam_without_evidence_rejected`, `::test_wrong_recipient_with_evidence_accepted`, `::test_scam_with_evidence_accepted` | None |
| Evidence optional for debited_not_credited & duplicate | PASS | `tests/test_regression.py::test_debited_not_credited_without_evidence_accepted`, `::test_duplicate_without_evidence_accepted` | None |
| Validation shared by create and validate endpoints | PASS | `src/services/dispute.py::validate_complaint_payload` called by both `file_new_complaint` and `DisputeController.validate_complaint` | None |

## 4. POST /complaints/validate

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| Endpoint exists | PASS | `src/routers/dispute.py` line 40-45 | None |
| Uses same validation rules as create | PASS | Both call `DisputeWorkflowService.validate_complaint_payload` | None |
| No side effects (no complaint/audit created) | PASS | `tests/test_regression.py::test_validate_does_not_create_complaint` asserts complaint count unchanged | None |
| Returns valid/invalid response | PASS | `tests/test_regression.py::test_validate_valid_complaint_returns_200` | None |

## 5. Complaint Queue & Detail

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| GET /complaints lists bank-filtered complaints | PASS | `src/services/dispute.py::browse_bank_ledger` filters by `user.bank` | None |
| GET /complaints/{id} enforces bank ownership | PASS | `src/services/dispute.py::fetch_permitted_complaint` checks `complaint.bank == user.bank` | None |
| Cross-bank read returns 404 (Greenbank→Bluemobile) | PASS | `tests/test_security_boundary.py::test_signature_cross_bank_isolation_boundary` | None |
| Cross-bank read returns 404 (Bluemobile→Greenbank) | PASS | `tests/test_security_boundary.py::test_cross_bank_isolation_reverse_direction` | None |
| Cross-bank read does not expose private details | PASS | `tests/test_security_boundary.py` asserts no `complaint_id`/`transfer_reference`/`description` in 404 body | None |

## 6. Local Hub Mock

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| POST /api/v1/customer-disputes exists | PASS | `src/routers/dispute.py` line 97-105 | None |
| Accepted registration returns claim ID | PASS | `tests/test_regression.py::test_hub_mock_accepted_registration_returns_claim_id` | None |
| Rejected registration (ref ends in 999) returns null claim ID | PASS | `tests/test_regression.py::test_hub_mock_rejected_registration_returns_null_claim_id` | None |
| No private data sent to hub | PASS | `tests/test_regression.py::test_hub_mock_no_private_data_in_request` | None |
| No external service calls | PASS | `src/services/dispute.py::mock_external_hub_call` is purely local | None |

## 7. Evidence Handling

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| Evidence stored as filename string only | PASS | `src/schemas/dispute.py` `evidence: Optional[str] = None`; no file upload endpoint | None |
| Frontend does not claim file upload | PASS | `frontend/src/App.tsx` labels evidence as "filename stored only; file not uploaded" | None |

## 8. Database & Persistence

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| SQLite database used | PASS | `database.py` uses `sqlite3.connect` | None |
| Complaints table schema | PASS | `database.py::init_db()` creates `complaints` table | None |
| Audit logs table schema | PASS | `database.py::init_db()` creates `audit_logs` table | None |
| Bank ownership column on complaints | PASS | `complaints.bank` TEXT NOT NULL | None |
| No `operators` table (credentials in env) | PARTIAL | Credentials loaded from env vars; no operators table exists | Consider adding operators table for production |
| Synthetic seed script available | PASS | `backend/seed_demo_data.py` — requires explicit `--db` or `DISPUTE_DB_PATH`, never overwrites | None |
| Real development DB never touched by tests | PASS | Tests patch `database.DB_FILE` to temp file; mtime verified unchanged | None |

## 9. Security

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| Bank derived from server-side token, not request body | PASS | `src/services/auth.py` extracts `bank` from JWT payload; complaint creation uses `user.bank` | None |
| Protected endpoints enforce authentication | PASS | All complaint routes use `Depends(resolve_security_session)` | None |
| Errors include error codes | PASS | `core/error.py` defines `error_code` for each exception type | None |
| No stack traces in error responses | PASS | `core/error.py::app_error_handler` returns only `error_code` and `message` | None |
| Request ID in responses | PARTIAL | `SecurityTrackingMiddleware` sets `X-Request-ID` header; complaint creation passes `req_id` to audit log; error responses do NOT include request ID in body | Consider adding `request_id` to error JSON |
| No secrets in logs | PASS | `SecurityTrackingMiddleware` only logs request ID; audit logs exclude passwords/tokens/description | None |
| Tokens not printed to console | PASS | No `print()` or logging of tokens in backend or frontend | None |
| localStorage security risk documented | PASS | `frontend/src/App.tsx` documents localStorage vulnerability and recommends HttpOnly cookies | None |

## 10. Frontend Integration

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| Login/logout works | PASS | Frontend `handleLogin`/`handleLogout` use `/auth/login` contract | None |
| Error handling displays backend message | PASS | Frontend `errorMessage()` reads `data.message` / `data.error_code` | None |
| Form validation matches backend | PASS | Frontend validates `^TXN-\d{6}$`, positive decimal, 4 categories, evidence rules | None |
| validate endpoint called before submit | PASS | Frontend `validateComplaint()` called in `handleSubmitComplaint` | None |
| Queue refresh preserves selection | PASS | Frontend `loadComplaints` preserves selected complaint by ID | None |
| Detail uses GET /complaints/{id} | PASS | Frontend `fetchComplaintDetail()` | None |
| Registration acceptance/rejection displayed | PASS | Frontend shows `hub_claim_id` and `hub_error_message` | None |
| Loading/success/empty states | PASS | Frontend has `loading`, `successMsg`, `errorMsg`, empty queue message | None |
| API base URL configurable via env | PASS | `frontend/.env.example` with `VITE_API_BASE`; `import.meta.env.VITE_API_BASE` | None |
| Build passes | PASS | `npm run build` succeeds (tsc + vite build) | None |
| Lint passes | PARTIAL | `npm run lint` fails due to typescript-eslint/TypeScript 7.0 incompatibility (pre-existing, not caused by changes) | Upgrade typescript-eslint or pin TypeScript < 7 |

## 11. Documentation

| Requirement | Status | Evidence / Verification | Next Action |
|-------------|--------|------------------------|-------------|
| Backend README | PASS | `backend/README.md` — purpose, architecture, prerequisites, env config, startup, Swagger, test commands, endpoints, validation, security | None |
| Frontend README | PASS | `frontend/README.md` — prerequisites, install, dev, env config, build, lint | None |
| Architecture diagram (Mermaid) | PASS | `backend/architecture.mmd` | None |
| `.env.example` files | PASS | `backend/.env.example`, `frontend/.env.example` — placeholders only | None |

## 12. Remaining Limitations

1. **Error responses lack request ID in body**: The `X-Request-ID` header is set, but error JSON bodies do not include `request_id`.
2. **No operators table**: Credentials are loaded from environment variables. For production, consider a proper operators table with hashed passwords.
3. **Token revocation**: Tokens are stateless JWT-like tokens with no blocklist/rotation mechanism.
4. **localStorage token storage**: Vulnerable to XSS. HttpOnly cookies would require backend cookie support.
5. **Evidence is filename only**: No file upload endpoint exists.
6. **Lint toolchain**: `typescript-eslint` is incompatible with TypeScript 7.0.x pinned in the project.
7. **No frontend automated tests**: Manual testing recommended.
