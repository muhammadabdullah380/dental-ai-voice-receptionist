from sqlalchemy.orm import Session
from app.models.patient import Patient


def get_patient_by_phone(db: Session, phone_number: str):
    return db.query(Patient).filter(Patient.phone_number == phone_number).first()


def create_patient(db: Session, name: str, phone_number: str, email: str = None):
    existing = get_patient_by_phone(db, phone_number)
    if existing:
        return existing  # avoid duplicate patient records
    patient = Patient(name=name, phone_number=phone_number, email=email)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient