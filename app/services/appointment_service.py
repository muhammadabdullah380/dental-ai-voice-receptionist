import logging
import threading
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, CallLog
from app.integrations.factory import calendar_provider, logging_provider
from app.services import patient_service
from app.config import settings

logger = logging.getLogger("uvicorn.error")

# Simple in-process lock to prevent double-booking during concurrent requests.
_booking_lock = threading.Lock()

APPOINTMENT_WEBHOOK_URL = getattr(
    settings, "N8N_APPOINTMENT_WEBHOOK_URL", "http://localhost:5678/webhook/appointment-booked"
)
CALL_SUMMARY_WEBHOOK_URL = getattr(
    settings, "N8N_CALL_SUMMARY_WEBHOOK_URL", "http://localhost:5678/webhook/call-summary"
)


class CalendarUnavailableError(Exception):
    """Raised when the calendar provider (Google Calendar) fails or is unreachable."""
    pass


def _localize(dt: datetime) -> datetime:
    """Ensure a datetime has the clinic's timezone attached before comparing."""
    tz = ZoneInfo(settings.CLINIC_TIMEZONE)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _resolve_patient_name(db: Session, patient_id: str) -> str:
    if not patient_id:
        return "Unknown"
    try:
        patient = patient_service.get_patient_by_id(db, patient_id)
        return patient.name if patient else patient_id
    except Exception as e:
        logger.warning(f"Could not resolve patient name for {patient_id}: {e}")
        return patient_id


def _send_webhook(url: str, payload: dict, label: str):
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"n8n {label} webhook delivered successfully ({url})")
    except httpx.TimeoutException:
        logger.warning(f"n8n {label} webhook timed out ({url}) — Sheets log was NOT created, but the operation itself succeeded.")
    except httpx.HTTPStatusError as e:
        logger.warning(f"n8n {label} webhook returned {e.response.status_code} ({url}) — Sheets log may not have been created.")
    except httpx.RequestError as e:
        logger.warning(f"n8n {label} webhook unreachable ({url}): {e} — is n8n running? Sheets log was NOT created.")
    except Exception as e:
        logger.warning(f"Unexpected error sending n8n {label} webhook: {e}")


def _send_appointment_log(db: Session, appointment, status: str):
    _send_webhook(
        APPOINTMENT_WEBHOOK_URL,
        {
            "appointment_id": str(appointment.id),
            "patient_name": _resolve_patient_name(db, appointment.patient_id),
            "appointment_type": appointment.appointment_type,
            "start_time": str(appointment.start_time),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        },
        label="appointment log",
    )


def get_available_slots(date: datetime, provider: str = None):
    try:
        return calendar_provider.get_available_slots(
            date=date,
            duration_minutes=settings.APPOINTMENT_DURATION_MIN,
            provider=provider,
        )
    except Exception as e:
        logger.error(f"Calendar error while fetching available slots for {date}: {e}", exc_info=True)
        raise CalendarUnavailableError(
            "Could not check calendar availability right now. Please try again in a moment."
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
        try:
            free_slots = calendar_provider.get_available_slots(
                date=start_time, duration_minutes=settings.APPOINTMENT_DURATION_MIN
            )
        except Exception as e:
            logger.error(f"Calendar error while checking slot availability: {e}", exc_info=True)
            raise CalendarUnavailableError("Could not verify calendar availability right now. Please try again shortly.")

        slot_still_free = any(s["start"] == start_time for s in free_slots)
        if not slot_still_free:
            raise ValueError("Requested slot is no longer available")

        try:
            event_id = calendar_provider.create_event(
                start=start_time, end=end_time, title=f"{appointment_type} - Patient {patient_id}"
            )
        except Exception as e:
            logger.error(f"Calendar error while creating event for patient {patient_id}: {e}", exc_info=True)
            raise CalendarUnavailableError("Could not create the calendar event right now. Please try again shortly.")

        try:
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
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while saving appointment for patient {patient_id}: {e}", exc_info=True)
            try:
                calendar_provider.cancel_event(event_id)
            except Exception as cleanup_error:
                logger.error(f"Failed to roll back orphaned calendar event {event_id}: {cleanup_error}")
            raise ValueError("Could not save the appointment. Please try again.")

    logger.info(f"Appointment {appointment.id} booked for patient {patient_id} at {start_time}")

    try:
        logging_provider.log_appointment({
            "patient_id": patient_id,
            "appointment_id": appointment.id,
            "start_time": str(start_time),
            "type": appointment_type,
            "status": "confirmed",
        })
    except Exception as e:
        logger.warning(f"logging_provider.log_appointment failed (non-fatal): {e}")

    _send_appointment_log(db, appointment, "confirmed")

    return appointment


def reschedule_appointment(db: Session, appointment_id: str, new_start_time: datetime):
    new_start_time = _localize(new_start_time)

    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    new_end_time = new_start_time + timedelta(minutes=settings.APPOINTMENT_DURATION_MIN)

    with _booking_lock:
        try:
            free_slots = calendar_provider.get_available_slots(
                date=new_start_time, duration_minutes=settings.APPOINTMENT_DURATION_MIN
            )
        except Exception as e:
            logger.error(f"Calendar error while checking new slot for appointment {appointment_id}: {e}", exc_info=True)
            raise CalendarUnavailableError("Could not verify calendar availability right now. Please try again shortly.")

        slot_still_free = any(s["start"] == new_start_time for s in free_slots)
        if not slot_still_free:
            raise ValueError("Requested new slot is not available")

        if appointment.external_event_id:
            try:
                calendar_provider.update_event(appointment.external_event_id, new_start_time, new_end_time)
            except Exception as e:
                logger.error(f"Calendar error while updating event for appointment {appointment_id}: {e}", exc_info=True)
                raise CalendarUnavailableError("Could not update the calendar event right now. Please try again shortly.")

        try:
            appointment.start_time = new_start_time
            appointment.end_time = new_end_time
            appointment.status = "rescheduled"
            db.commit()
            db.refresh(appointment)
        except Exception as e:
            db.rollback()
            logger.error(f"Database error while rescheduling appointment {appointment_id}: {e}", exc_info=True)
            raise ValueError("Could not save the rescheduled appointment. Please try again.")

    logger.info(f"Appointment {appointment.id} rescheduled to {new_start_time}")

    try:
        logging_provider.log_appointment({
            "appointment_id": appointment.id,
            "new_start_time": str(new_start_time),
            "status": "rescheduled",
        })
    except Exception as e:
        logger.warning(f"logging_provider.log_appointment failed (non-fatal): {e}")

    _send_appointment_log(db, appointment, "rescheduled")

    return appointment


def cancel_appointment(db: Session, appointment_id: str):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise ValueError("Appointment not found")

    if appointment.external_event_id:
        try:
            calendar_provider.cancel_event(appointment.external_event_id)
        except Exception as e:
            logger.error(f"Calendar error while cancelling event for appointment {appointment_id}: {e}", exc_info=True)

    try:
        appointment.status = "cancelled"
        db.commit()
        db.refresh(appointment)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error while cancelling appointment {appointment_id}: {e}", exc_info=True)
        raise ValueError("Could not save the cancellation. Please try again.")

    logger.info(f"Appointment {appointment.id} cancelled")

    try:
        logging_provider.log_appointment({
            "appointment_id": appointment.id,
            "status": "cancelled",
        })
    except Exception as e:
        logger.warning(f"logging_provider.log_appointment failed (non-fatal): {e}")

    _send_appointment_log(db, appointment, "cancelled")

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
    call_duration_seconds: int = None,
):
    try:
        call_log = CallLog(
            call_id=call_id,
            caller_number=caller_number,
            patient_id=patient_id,
            call_reason=call_reason,
            summary=summary,
            outcome=outcome,
            appointment_created=appointment_created,
            call_duration_seconds=call_duration_seconds,
        )
        db.add(call_log)
        db.commit()
        db.refresh(call_log)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error while saving call summary for call {call_id}: {e}", exc_info=True)
        raise ValueError("Could not save the call summary. Please try again.")

    logger.info(f"Call summary saved for call {call_id} (outcome: {outcome})")

    try:
        logging_provider.log_call_summary({
            "call_id": call_id,
            "summary": summary,
            "outcome": outcome,
        })
    except Exception as e:
        logger.warning(f"logging_provider.log_call_summary failed (non-fatal): {e}")

    patient_name = _resolve_patient_name(db, patient_id)

    _send_webhook(
        CALL_SUMMARY_WEBHOOK_URL,
        {
            "call_id": call_id,
            "caller_number": caller_number,
            "patient_name": patient_name,
            "call_reason": call_reason,
            "summary": summary,
            "outcome": outcome,
            "appointment_created": appointment_created,
            "call_duration_seconds": call_duration_seconds,
            "timestamp": datetime.utcnow().isoformat(),
        },
        label="call summary",
    )

    return call_log