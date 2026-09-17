from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Experience, Project
from app.routes import router

PROJECT_SEED = [
    ("Dental AI Voice Receptionist", "FastAPI, Vapi, n8n, MCP, Calendar and Sheets.", "aether", "2026", 1),
    ("REST API Platforms", "Django, FastAPI, authentication and business logic.", "north", "2023-26", 2),
    ("Automation Workflows", "Webhooks, integrations and reliable backend workflows.", "pulse", "2023-26", 3),
]

EXPERIENCE_SEED = [
    ("2023 - 2026", "Python Backend Developer", "Professional Experience", "Designed and developed backend applications using Python and Django, RESTful APIs, PostgreSQL, authentication, validation, and business logic.", 1),
    ("2023 - 2026", "API & Integration Developer", "Professional Experience", "Integrated external APIs and services using REST APIs and webhooks, while building data processing and automation workflows.", 2),
    ("2023 - 2026", "AI Integration Developer", "Professional Experience", "Worked with AI integration, voice AI, Vapi, MCP, and n8n workflow automation for real-world business applications.", 3),
    ("2023 - 2026", "Deployment & Infrastructure", "Professional Experience", "Used Docker for containerization and contributed to cloud deployment with AWS and Render.", 4),
]


def seed_content(db: Session):
    if not db.scalar(select(Project.id).limit(1)):
        db.add_all([Project(name=name, detail=detail, project_type=project_type, year=year, sort_order=sort_order) for name, detail, project_type, year, sort_order in PROJECT_SEED])
    if not db.scalar(select(Experience.id).limit(1)):
        db.add_all([Experience(period=period, role=role, company=company, detail=detail, sort_order=sort_order) for period, role, company, detail, sort_order in EXPERIENCE_SEED])
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_content(db)
    yield


app = FastAPI(
    title="Muhammad ABDULLAH Portfolio API",
    description="Backend API for projects, experience, and portfolio contact messages.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "portfolio-api"}
