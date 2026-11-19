from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from backend.database import init_db
from backend.schemas import HealthResponse
from backend.api.investigations import router as inv_router
from backend.api.uploads import router as upload_router
from backend.api.analysis import router as analysis_router
from backend.api.settings import router as settings_router

app = FastAPI(title="TruthLens", description="Multimodal Digital Forensics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inv_router)
app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(settings_router)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/api/v1/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", version="1.0.0", timestamp=datetime.now(timezone.utc))
