import sys
import os

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

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
