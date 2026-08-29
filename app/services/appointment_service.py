import threading
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, CallLog
from app.integrations.factory import calendar_provider, logging_provider
from app.config import settings

# Simple in-process lock to prevent double-booking during concurrent requests.
_booking_lock = threading.Lock()

APPOINTMENT_WEBHOOK_URL = "http://localhost:5678/webhook/appointment-booked"


def _localize(dt: datetime) -> datetime:
    """Ensure a datetime has the clinic's timezone attached before comparing."""
    tz = ZoneInfo(settings.CLINIC_TIMEZONE)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _send_appointment_log(appointment, status: str):
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                APPOINTMENT_WEBHOOK_URL,
                json={
                    "appointment_id": str(appointment.id),
                    "patient_name": appointment.patient_id,
                    "appointment_type": appointment.appointment_type,
                    "start_time": str(appointment.start_time),
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
    except Exception as e:
        print(f"n8n ko appointment log bhejne mein masla: {e}")


def get_available_slots(date: datetime, provider: str = None):
    return calendar_provider.get_available_slots(
        date=date,
        duration_minutes=settings.APPOINTMENT_DURATION_MIN,
        provider=provider,
    )


def book_appointment(
    db: Session,
    patient_id: str,
    start_time: datetime,
    appointment_type: str = "General Checkup",
    provider: str = None,
):
    start_time = _localize(start_time)
    end_time = start_time + timedelta(minutes=settings.APPOINTMENT_DURATION_MIN)

    with _booking_lock:
        free_slots = calendar_provider.get_available_slots(
            date=start_time, duration_minutes=settings.APPOINTMENT_DURATION_MIN
        )
        slot_still_free = any(s["start"] == start_time for s in free_slots)
        if not slot_still_free:
            raise ValueError("Requested slot is no longer available")

        event_id = calendar_provider.create_event(
            start=start_time, end=end_time, title=f"{appointment_type} - Patient {patient_id}"
        )

        appointment = Appointment(
            patient_id=patient_id,
            appointment_type=appointment_type,
            provider=provider,
            start_time=start_time,
            end_time=end_time,
            status="confirmed",
            external_event_id=event_id,
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

    logging_provider.log_appointment({
        "patient_id": patient_id,
        "appointment_id": appointment.id,
        "start_time": str(start_time),
        "type": appointment_type,
        "status": "confirmed",
    })

    _send_appointment_log(appointment, "confirmed")

    return appointment


def reschedule_appointment(db: Session, appointment_id: str, new_start_time: datetime):
    new_start_time = _localize(new_start_time)

    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    new_end_time = new_start_time + timedelta(minutes=settings.APPOINTMENT_DURATION_MIN)

    with _booking_lock:
        free_slots = calendar_provider.get_available_slots(
            date=new_start_time, duration_minutes=settings.APPOINTMENT_DURATION_MIN
        )
        slot_still_free = any(s["start"] == new_start_time for s in free_slots)
        if not slot_still_free:
            raise ValueError("Requested new slot is not available")

        if appointment.external_event_id:
            calendar_provider.update_event(appointment.external_event_id, new_start_time, new_end_time)

        appointment.start_time = new_start_time
        appointment.end_time = new_end_time
        appointment.status = "rescheduled"
        db.commit()
        db.refresh(appointment)

    logging_provider.log_appointment({
        "appointment_id": appointment.id,
        "new_start_time": str(new_start_time),
        "status": "rescheduled",
    })

    _send_appointment_log(appointment, "rescheduled")

    return appointment


def cancel_appointment(db: Session, appointment_id: str):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    if appointment.external_event_id:
        calendar_provider.cancel_event(appointment.external_event_id)

    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)

    logging_provider.log_appointment({
        "appointment_id": appointment.id,
        "status": "cancelled",
    })

    _send_appointment_log(appointment, "cancelled")

    return appointment


def save_call_summary(
    db: Session,
    call_id: str,
    caller_number: str = None,
    patient_id: str = None,
    call_reason: str = None,
    summary: str = None,
    outcome: str = None,
    appointment_created: str = None,
):
    call_log = CallLog(
        call_id=call_id,
        caller_number=caller_number,
        patient_id=patient_id,
        call_reason=call_reason,
        summary=summary,
        outcome=outcome,
        appointment_created=appointment_created,
    )
    db.add(call_log)
    db.commit()
    db.refresh(call_log)

    logging_provider.log_call_summary({
        "call_id": call_id,
        "summary": summary,
        "outcome": outcome,
    })

    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                "http://localhost:5678/webhook/call-summary",
                json={
                    "call_id": call_id,
                    "caller_number": caller_number,
                    "patient_name": patient_id,
                    "call_reason": call_reason,
                    "summary": summary,
                    "outcome": outcome,
                    "appointment_created": appointment_created,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
    except Exception as e:
        print(f"n8n ko call summary bhejne mein masla: {e}")

    return call_log