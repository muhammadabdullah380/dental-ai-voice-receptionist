import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dental.db")

    # Which providers to use — this is how you "swap" integrations later
    # without touching business logic. Just change these env vars.
    CALENDAR_PROVIDER: str = os.getenv("CALENDAR_PROVIDER", "mock")  # mock | google
    LOGGING_PROVIDER: str = os.getenv("LOGGING_PROVIDER", "mock")    # mock | sheets

    # Google (used later once we swap providers)
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")

    # Clinic defaults (later: load per-clinic from DB/config file)
    CLINIC_NAME: str = os.getenv("CLINIC_NAME", "Bright Smile Dental")
    CLINIC_TIMEZONE: str = os.getenv("CLINIC_TIMEZONE", "Asia/Karachi")
    APPOINTMENT_DURATION_MIN: int = int(os.getenv("APPOINTMENT_DURATION_MIN", "30"))


settings = Settings()