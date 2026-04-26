from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import prescriptions, health
import structlog

log = structlog.get_logger()

app = FastAPI(
    title="Medical Prescription Explainer",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(prescriptions.router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    log.info("rx-explainer starting", env=settings.environment)
