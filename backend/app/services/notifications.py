import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def notify_server_created(
    server_name: str,
    server_slug: str,
    owner_username: str,
) -> None:
    """
    Notify site admin(s) that a new server has been created.
    Always logs to stdout (visible in docker compose logs).
    Sends an email if SMTP_HOST and SMTP_ADMIN_EMAIL are configured.
    Email failures never propagate — a broken mail server must not prevent
    server creation from succeeding.
    """
    logger.info(
        "SERVER_CREATED | slug=%s owner=%s domain=%s",
        server_slug,
        owner_username,
        settings.SERVER_DOMAIN,
    )

    if not (settings.SMTP_HOST and settings.SMTP_ADMIN_EMAIL):
        return

    body = (
        f"New server created on {settings.SERVER_DOMAIN}\n"
        f"  Name:   {server_name}\n"
        f"  Slug:   {server_slug}\n"
        f"  Owner:  {owner_username}\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = f"[Chisme] New server created: {server_name}"
    msg["From"] = settings.SMTP_FROM_EMAIL or f"chisme@{settings.SERVER_DOMAIN}"
    msg["To"] = settings.SMTP_ADMIN_EMAIL

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Operator notification email sent to %s", settings.SMTP_ADMIN_EMAIL)
    except Exception as exc:
        logger.warning("Failed to send operator notification email: %s", exc)
