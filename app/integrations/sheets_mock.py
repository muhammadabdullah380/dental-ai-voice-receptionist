from app.integrations.base import LoggingProvider


class MockLoggingProvider(LoggingProvider):
    """
    Prints to console instead of writing to Google Sheets.
    Swap for GoogleSheetsProvider later by changing
    LOGGING_PROVIDER=sheets in .env.
    """

    def log_appointment(self, appointment: dict) -> None:
        print(f"[MOCK SHEETS] Appointment logged: {appointment}")

    def log_call_summary(self, call_log: dict) -> None:
        print(f"[MOCK SHEETS] Call summary logged: {call_log}")