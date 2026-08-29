"""
Abstract interfaces for external systems.

This is THE key architectural piece the project spec asks for:
"The architecture should allow us to later replace Google Calendar ->
Dental PMS/EHR/CRM, and Google Sheets -> Clinic Database/PMS/CRM."

Business logic (in services/) only ever talks to these interfaces,
never directly to Google APIs. To add a new clinic system, write a
new class that implements these methods — nothing else changes.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional


class CalendarProvider(ABC):
    @abstractmethod
    def get_available_slots(
        self, date: datetime, duration_minutes: int, provider: Optional[str] = None
    ) -> List[dict]:
        """Return list of {"start": datetime, "end": datetime} free slots."""
        ...

    @abstractmethod
    def create_event(
        self, start: datetime, end: datetime, title: str, description: str = ""
    ) -> str:
        """Create calendar event, return external_event_id."""
        ...

    @abstractmethod
    def update_event(self, event_id: str, start: datetime, end: datetime) -> None:
        ...

    @abstractmethod
    def cancel_event(self, event_id: str) -> None:
        ...


class LoggingProvider(ABC):
    @abstractmethod
    def log_appointment(self, appointment: dict) -> None:
        ...

    @abstractmethod
    def log_call_summary(self, call_log: dict) -> None:
        ...