from sqlalchemy.orm import Session
from app.models.patient import Patient


def get_patient_by_phone(db: Session, phone_number: str):
    return db.query(Patient).filter(Patient.phone_number == phone_number).first()


def get_patient_by_id(db: Session, patient_id: str):
    """Looks up a patient by their internal ID. Used when we only have a
    patient_id on hand (e.g. an appointment or call log) but need their name
    for a human-readable log or Sheet row."""
    if not patient_id:
        return None
    return db.query(Patient).filter(Patient.id == patient_id).first()


def create_patient(db: Session, name: str, phone_number: str, email: str = None):
    existing = get_patient_by_phone(db, phone_number)
    if existing:
        return existing  # avoid duplicate patient records
    patient = Patient(name=name, phone_number=phone_number, email=email)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient