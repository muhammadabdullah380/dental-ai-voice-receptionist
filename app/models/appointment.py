import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func
from app.db.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    appointment_type = Column(String, nullable=False, default="General Checkup")
    provider = Column(String, nullable=True)  # dentist name, for multi-provider later
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="confirmed")  # confirmed|cancelled|rescheduled
    external_event_id = Column(String, nullable=True)  # Google Calendar event id, once wired up
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    call_id = Column(String, nullable=False, index=True)
    caller_number = Column(String, nullable=True)
    patient_id = Column(String, nullable=True)
    call_reason = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    outcome = Column(String, nullable=True)  # booked|rescheduled|cancelled|faq|no_action
    appointment_created = Column(String, nullable=True)  # yes/no, or appointment_id
    call_duration_seconds = Column(Integer, nullable=True)  # total call length, sent by Vapi
    created_at = Column(DateTime(timezone=True), server_default=func.now())