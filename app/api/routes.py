import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import appointment_service, patient_service
from app.config import settings

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


# ---------- Vapi webhook helpers ----------
# Vapi sends tool calls wrapped like:
# {"message": {"toolCallList": [{"id": "...", "function": {"name": "...", "arguments": {...}}}]}}
# and expects a response shaped like:
# {"results": [{"toolCallId": "...", "result": "..."}]}
# These two helpers extract the real arguments and build the expected response,
# regardless of the exact wrapper shape Vapi sends.

def extract_tool_call(payload: dict):
    """Returns (tool_call_id, arguments_dict) from a Vapi tool-call webhook payload."""
    message = payload.get("message", payload)  # fall back to flat payload if no wrapper
    tool_calls = message.get("toolCallList") or message.get("toolCalls") or []

    if not tool_calls:
        raise ValueError(f"No tool call found in payload: {payload}")

    call = tool_calls[0]
    tool_call_id = call.get("id") or call.get("toolCallId", "unknown")
    function = call.get("function", {})
    arguments = function.get("arguments", {})

    # arguments sometimes arrives as a JSON string instead of a dict
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}

    return tool_call_id, arguments


def vapi_result(tool_call_id: str, result):
    """Wraps a result in the shape Vapi expects back from a tool call."""
    if not isinstance(result, str):
        result = json.dumps(result, default=str)
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


async def parse_and_validate(request: Request, schema: type[BaseModel]):
    """Reads the raw Vapi webhook body, extracts args, validates against schema.
    Returns (tool_call_id, validated_request_or_None, error_message_or_None).
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error(f"Could not parse JSON body: {raw_body}")
        return "unknown", None, "Invalid JSON received"

    try:
        tool_call_id, arguments = extract_tool_call(payload)
    except ValueError as e:
        logger.error(str(e))
        return "unknown", None, str(e)

    try:
        validated = schema(**arguments)
    except ValidationError as e:
        logger.error(f"VALIDATION FAILED for {schema.__name__}")
        logger.error(f"ARGUMENTS RECEIVED: {arguments}")
        logger.error(f"ERRORS: {e.errors()}")
        return tool_call_id, None, f"Invalid arguments: {e.errors()}"

    return tool_call_id, validated, None


# ---------- Schemas ----------

class SlotsRequest(BaseModel):
    date: datetime
    provider: Optional[str] = None


class BookAppointmentRequest(BaseModel):
    patient_id: str
    start_time: datetime
    appointment_type: str = "General Checkup"
    provider: Optional[str] = None


class RescheduleRequest(BaseModel):
    appointment_id: str
    new_start_time: datetime


class CancelRequest(BaseModel):
    appointment_id: str


class CreatePatientRequest(BaseModel):
    name: str
    phone_number: str
    email: Optional[str] = None


class GetPatientRequest(BaseModel):
    phone_number: str


class CallSummaryRequest(BaseModel):
    call_id: str
    caller_number: Optional[str] = None
    patient_id: Optional[str] = None
    call_reason: Optional[str] = None
    summary: Optional[str] = None
    outcome: Optional[str] = None
    appointment_created: Optional[str] = None


# ---------- Tool 1: get_available_slots ----------

@router.post("/tools/get_available_slots")
async def get_available_slots(request: Request):
    tool_call_id, req, error = await parse_and_validate(request, SlotsRequest)
    if error:
        return vapi_result(tool_call_id, error)

    slots = appointment_service.get_available_slots(date=req.date, provider=req.provider)
    return vapi_result(tool_call_id, {"slots": slots})


# ---------- Tool 2: book_appointment ----------

@router.post("/tools/book_appointment")
async def book_appointment(request: Request, db: Session = Depends(get_db)):
    tool_call_id, req, error = await parse_and_validate(request, BookAppointmentRequest)
    if error:
        return vapi_result(tool_call_id, error)

    try:
        appointment = appointment_service.book_appointment(
            db=db,
            patient_id=req.patient_id,
            start_time=req.start_time,
            appointment_type=req.appointment_type,
            provider=req.provider,
        )
        return vapi_result(tool_call_id, {
            "success": True,
            "appointment_id": appointment.id,
            "status": appointment.status,
        })
    except ValueError as e:
        return vapi_result(tool_call_id, f"Could not book appointment: {e}")


# ---------- Tool 3: reschedule_appointment ----------

@router.post("/tools/reschedule_appointment")
async def reschedule_appointment(request: Request, db: Session = Depends(get_db)):
    tool_call_id, req, error = await parse_and_validate(request, RescheduleRequest)
    if error:
        return vapi_result(tool_call_id, error)

    try:
        appointment = appointment_service.reschedule_appointment(
            db=db, appointment_id=req.appointment_id, new_start_time=req.new_start_time
        )
        return vapi_result(tool_call_id, {
            "success": True,
            "appointment_id": appointment.id,
            "status": appointment.status,
        })
    except ValueError as e:
        return vapi_result(tool_call_id, f"Could not reschedule appointment: {e}")


# ---------- Tool 4: cancel_appointment ----------

@router.post("/tools/cancel_appointment")
async def cancel_appointment(request: Request, db: Session = Depends(get_db)):
    tool_call_id, req, error = await parse_and_validate(request, CancelRequest)
    if error:
        return vapi_result(tool_call_id, error)

    try:
        appointment = appointment_service.cancel_appointment(db=db, appointment_id=req.appointment_id)
        return vapi_result(tool_call_id, {
            "success": True,
            "appointment_id": appointment.id,
            "status": appointment.status,
        })
    except ValueError as e:
        return vapi_result(tool_call_id, f"Could not cancel appointment: {e}")


# ---------- Tool 5: get_patient ----------

@router.post("/tools/get_patient")
async def get_patient(request: Request, db: Session = Depends(get_db)):
    tool_call_id, req, error = await parse_and_validate(request, GetPatientRequest)
    if error:
        return vapi_result(tool_call_id, error)

    patient = patient_service.get_patient_by_phone(db, req.phone_number)
    if not patient:
        return vapi_result(tool_call_id, "No patient found with that phone number.")

    return vapi_result(tool_call_id, {
        "id": patient.id,
        "name": patient.name,
        "phone_number": patient.phone_number,
    })


# ---------- Tool 6: create_patient ----------

@router.post("/tools/create_patient")
async def create_patient(request: Request, db: Session = Depends(get_db)):
    tool_call_id, req, error = await parse_and_validate(request, CreatePatientRequest)
    if error:
        return vapi_result(tool_call_id, error)

    patient = patient_service.create_patient(db, req.name, req.phone_number, req.email)
    return vapi_result(tool_call_id, {
        "id": patient.id,
        "name": patient.name,
        "phone_number": patient.phone_number,
    })


# ---------- Tool 7: get_clinic_information ----------

@router.post("/tools/get_clinic_information")
async def get_clinic_information(request: Request):
    raw_body = await request.body()
    tool_call_id = "unknown"
    try:
        payload = json.loads(raw_body) if raw_body else {}
        tool_call_id, _ = extract_tool_call(payload)
    except (json.JSONDecodeError, ValueError):
        pass  # no args needed for this tool anyway

    info = {
        "clinic_name": settings.CLINIC_NAME,
        "timezone": settings.CLINIC_TIMEZONE,
        "hours": "Mon-Sat 9:00 AM - 5:00 PM",
        "location": "123 Main Street",
        "services": ["Cleaning", "Checkup", "Filling", "Root Canal", "Whitening"],
        "insurance": "Most major insurance accepted, please confirm at booking.",
        "emergency_instructions": "For dental emergencies after hours, call our emergency line.",
    }
    return vapi_result(tool_call_id, info)


# ---------- Tool 8: save_call_summary ----------

@router.post("/tools/save_call_summary")
async def save_call_summary(request: Request, db: Session = Depends(get_db)):
    tool_call_id, req, error = await parse_and_validate(request, CallSummaryRequest)
    if error:
        return vapi_result(tool_call_id, error)

    call_log = appointment_service.save_call_summary(
        db=db,
        call_id=req.call_id,
        caller_number=req.caller_number,
        patient_id=req.patient_id,
        call_reason=req.call_reason,
        summary=req.summary,
        outcome=req.outcome,
        appointment_created=req.appointment_created,
    )
    return vapi_result(tool_call_id, {"success": True, "call_log_id": call_log.id})
