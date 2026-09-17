import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    database_url = os.getenv("PORTFOLIO_DATABASE_URL", f"sqlite:///{BASE_DIR / 'portfolio.db'}")
    frontend_url = os.getenv("PORTFOLIO_FRONTEND_URL", "http://localhost:5173")
    smtp_host = os.getenv("PORTFOLIO_SMTP_HOST", "")
    smtp_port = int(os.getenv("PORTFOLIO_SMTP_PORT", "587"))
    smtp_username = os.getenv("PORTFOLIO_SMTP_USERNAME", "")
    smtp_password = os.getenv("PORTFOLIO_SMTP_PASSWORD", "")
    contact_recipient = os.getenv("PORTFOLIO_CONTACT_RECIPIENT", "abdullahkhannutmn@gmail.com")
    smtp_from = os.getenv("PORTFOLIO_SMTP_FROM", smtp_username)
    frontend_origins = [
        frontend_url,
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]


settings = Settings()
