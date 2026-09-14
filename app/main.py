import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI
from app.api.routes import router
from app.db.database import Base, engine

# Create tables on startup (fine for dev; use Alembic migrations later)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dental AI Receptionist Backend",
    description="Core API layer that MCP tools call into. "
                 "Vapi -> MCP Server -> this backend -> Calendar/Sheets/PMS.",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("uvicorn.error")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    body = await request.body()
    logger.error(f"VALIDATION FAILED on {request.url.path}")
    logger.error(f"RAW BODY: {body}")
    logger.error(f"ERRORS: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "validation_failed", "detail": exc.errors()},
    )