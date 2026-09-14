import logging

from app.config import settings
from app.integrations.calendar_mock import MockCalendarProvider
from app.integrations.sheets_mock import MockLoggingProvider
from app.integrations.calendar_google import GoogleCalendarProvider

# When you build the real one later:
# from app.integrations.sheets_google import GoogleSheetsProvider

logger = logging.getLogger("uvicorn.error")


def get_calendar_provider():
    if settings.CALENDAR_PROVIDER == "google":
        return GoogleCalendarProvider()
    return MockCalendarProvider()


def get_logging_provider():
    if settings.LOGGING_PROVIDER == "sheets":
        logger.warning(
            "Google Sheets logging is configured but not implemented yet; falling back to mock logging provider."
        )
    return MockLoggingProvider()


# Singletons — mock calendar needs to persist bookings across requests
# within a dev session, so we keep one instance app-wide.
calendar_provider = get_calendar_provider()
logging_provider = get_logging_provider()