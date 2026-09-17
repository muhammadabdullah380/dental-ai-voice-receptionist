from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.email_service import send_contact_email
from app.models import ContactMessage, Experience, Project
from app.schemas import ContactCreate, ContactResponse, ExperienceResponse, ProjectResponse

router = APIRouter(prefix="/api")


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.sort_order, Project.id)).all()


@router.get("/experience", response_model=list[ExperienceResponse])
def list_experience(db: Session = Depends(get_db)):
    return db.scalars(select(Experience).order_by(Experience.sort_order, Experience.id)).all()


@router.post("/contact", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact_message(payload: ContactCreate, db: Session = Depends(get_db)):
    contact = ContactMessage(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    email_sent = send_contact_email(payload.name, payload.email, payload.message)
    return ContactResponse(
        id=contact.id,
        message=(
            "Thanks for reaching out. Muhammad will get back to you soon."
            if email_sent
            else "Your message was saved, but email delivery is not configured yet."
        ),
        created_at=contact.created_at,
    )
