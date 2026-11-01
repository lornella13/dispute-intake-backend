from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.dispute import router as dispute_router 

app = FastAPI(title="Dispute Intake Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dispute_router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Dispute Intake Backend is running"}
