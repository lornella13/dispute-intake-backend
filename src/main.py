import sys
import os

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)


def _load_env_file():
    """Load variables from .env into os.environ (without overriding existing env vars)."""
    env_path = os.path.join(BACKEND_ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


# Load .env before any module that reads environment variables is imported.
_load_env_file()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers.dispute import router
from middleware.logging import SecurityTrackingMiddleware
from core.error import register_exception_handlers

app = FastAPI(title="Dispute Intake Core Engine", version="1.0.0")

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityTrackingMiddleware)

init_db()

app.include_router(router)
