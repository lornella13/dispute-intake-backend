from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers.dispute import router
from middleware.logging import SecurityTrackingMiddleware
from core.error import register_exception_handlers  # Imported core error tracking

app = FastAPI(title="Dispute Intake Core Engine", version="1.0.0")

# Register global custom business & validation exception handlers
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
