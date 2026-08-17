import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import quote

from ..config import (
    MAIL_ENABLED,
    MAIL_FROM,
    MAIL_SMTP_HOST,
    MAIL_SMTP_PASSWORD,
    MAIL_SMTP_PORT,
    MAIL_SMTP_STARTTLS,
    MAIL_SMTP_USERNAME,
    MAIL_TIMEOUT_SECONDS,
    PUBLIC_APP_URL,
)


logger = logging.getLogger("enterprise_rag.email")


class EmailDeliveryError(RuntimeError):
    pass


def send_password_reset_email(*, recipient_email: str, reset_token: str, expires_at: datetime) -> None:
    if not MAIL_ENABLED:
        raise EmailDeliveryError("outbound email is disabled")

    reset_url = f"{PUBLIC_APP_URL.rstrip('/')}/password-reset?token={quote(reset_token, safe='')}"
    message = EmailMessage()
    message["Subject"] = "企业知识助手 - 密码重置"
    message["From"] = MAIL_FROM
    message["To"] = recipient_email
    message.set_content(
        "您的密码重置申请已获批准。\n\n"
        f"请在 {expires_at.isoformat()} UTC 前打开以下链接设置新密码：\n{reset_url}\n\n"
        "该链接仅可使用一次。若不是您本人提交的申请，请立即联系系统管理员。"
    )

    try:
        with smtplib.SMTP(MAIL_SMTP_HOST, MAIL_SMTP_PORT, timeout=MAIL_TIMEOUT_SECONDS) as client:
            client.ehlo()
            if MAIL_SMTP_STARTTLS:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if MAIL_SMTP_USERNAME:
                client.login(MAIL_SMTP_USERNAME, MAIL_SMTP_PASSWORD)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        logger.warning("Password reset email delivery failed: %s", error)
        raise EmailDeliveryError("password reset email could not be delivered") from error
