import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("uvicorn.error")


def send_contact_email(name: str, email: str, message: str) -> bool:
    if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from)):
        logger.warning("Contact email not sent: SMTP settings are not configured.")
        return False

    mail = EmailMessage()
    mail["Subject"] = f"New portfolio message from {name}"
    mail["From"] = settings.smtp_from
    mail["To"] = settings.contact_recipient
    mail["Reply-To"] = email
    mail.set_content(f"Name: {name}\nEmail: {email}\n\n{message}")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(mail)
        logger.info("Portfolio contact email sent to %s", settings.contact_recipient)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Contact email delivery failed")
        return False