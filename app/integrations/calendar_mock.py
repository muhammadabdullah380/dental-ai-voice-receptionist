import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from app.integrations.base import CalendarProvider


class MockCalendarProvider(CalendarProvider):
    """
    In-memory fake calendar. Lets you build/test the whole flow
    before touching real Google OAuth. Swap for GoogleCalendarProvider
    later by changing CALENDAR_PROVIDER=google in .env — nothing else
    in the codebase changes.
    """

    def __init__(self):
        # naive in-memory store: {event_id: {"start":, "end":, "title":}}
        self._events = {}

    def get_available_slots(
        self, date: datetime, duration_minutes: int, provider: Optional[str] = None
    ) -> List[dict]:
        # Fake business hours 9am-5pm, generate slots not already booked
        slots = []
        day_start = date.replace(hour=9, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=17, minute=0, second=0, microsecond=0)

        cursor = day_start
        booked_ranges = [(e["start"], e["end"]) for e in self._events.values()]

        while cursor + timedelta(minutes=duration_minutes) <= day_end:
            slot_end = cursor + timedelta(minutes=duration_minutes)
            overlaps = any(
                cursor < b_end and slot_end > b_start
                for b_start, b_end in booked_ranges
            )
            if not overlaps:
                slots.append({"start": cursor, "end": slot_end})
            cursor += timedelta(minutes=duration_minutes)

        return slots

    def create_event(
        self, start: datetime, end: datetime, title: str, description: str = ""
    ) -> str:
        event_id = str(uuid.uuid4())
        self._events[event_id] = {"start": start, "end": end, "title": title}
        return event_id

    def update_event(self, event_id: str, start: datetime, end: datetime) -> None:
        if event_id in self._events:
            self._events[event_id]["start"] = start
            self._events[event_id]["end"] = end

    def cancel_event(self, event_id: str) -> None:
        self._events.pop(event_id, None)