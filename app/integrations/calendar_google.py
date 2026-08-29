from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import settings
from app.integrations.base import CalendarProvider

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarProvider(CalendarProvider):
    """
    Real Google Calendar integration using a service account.
    Same interface as MockCalendarProvider — nothing else in the
    codebase needs to change to use this instead of the mock.
    """

    def __init__(self):
        self._calendar_id = settings.GOOGLE_CALENDAR_ID
        self._tz = ZoneInfo(settings.CLINIC_TIMEZONE)

        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        self._service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def _to_clinic_tz(self, dt: datetime) -> datetime:
        """Ensure a datetime is timezone-aware in the clinic's timezone."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self._tz)
        return dt.astimezone(self._tz)

    def get_available_slots(
        self, date: datetime, duration_minutes: int, provider: Optional[str] = None
    ) -> List[dict]:
        date = self._to_clinic_tz(date)
        day_start = date.replace(hour=9, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=17, minute=0, second=0, microsecond=0)

        events_result = self._service.events().list(
            calendarId=self._calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        busy_ranges = []
        for event in events_result.get("items", []):
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            end_raw = event["end"].get("dateTime", event["end"].get("date"))
            busy_start = datetime.fromisoformat(start_raw).astimezone(self._tz)
            busy_end = datetime.fromisoformat(end_raw).astimezone(self._tz)
            busy_ranges.append((busy_start, busy_end))

        slots = []
        cursor = day_start
        while cursor + timedelta(minutes=duration_minutes) <= day_end:
            slot_end = cursor + timedelta(minutes=duration_minutes)
            overlaps = any(
                cursor < b_end and slot_end > b_start
                for b_start, b_end in busy_ranges
            )
            if not overlaps:
                slots.append({"start": cursor, "end": slot_end})
            cursor += timedelta(minutes=duration_minutes)

        return slots

    def create_event(
        self, start: datetime, end: datetime, title: str, description: str = ""
    ) -> str:
        start = self._to_clinic_tz(start)
        end = self._to_clinic_tz(end)

        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": settings.CLINIC_TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": settings.CLINIC_TIMEZONE},
        }
        created_event = self._service.events().insert(
            calendarId=self._calendar_id, body=event_body
        ).execute()
        return created_event["id"]

    def update_event(self, event_id: str, start: datetime, end: datetime) -> None:
        start = self._to_clinic_tz(start)
        end = self._to_clinic_tz(end)

        event_body = {
            "start": {"dateTime": start.isoformat(), "timeZone": settings.CLINIC_TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": settings.CLINIC_TIMEZONE},
        }
        self._service.events().patch(
            calendarId=self._calendar_id, eventId=event_id, body=event_body
        ).execute()

    def cancel_event(self, event_id: str) -> None:
        self._service.events().delete(
            calendarId=self._calendar_id, eventId=event_id
        ).execute()