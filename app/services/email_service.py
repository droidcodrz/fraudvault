from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

from app.config import get_settings

logger = structlog.get_logger()


async def send_email(to: str, subject: str, html_body: str) -> None:
    settings = get_settings()

    if not settings.smtp_host:
        logger.info(
            "email_send_dev_mode",
            to=to,
            subject=subject,
            body_preview=html_body[:200],
        )
        return

    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=True,
    )
    logger.info("email_sent", to=to, subject=subject)


async def send_password_reset_email(to: str, token: str) -> None:
    settings = get_settings()
    reset_link = f"{settings.app_url}/#/reset-password?token={token}"
    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1a1a2e;">Reset Your Password</h2>
  <p>We received a request to reset the password for your FraudVault account.</p>
  <p>Click the button below to set a new password. This link expires in 1 hour.</p>
  <p style="text-align: center; margin: 32px 0;">
    <a href="{reset_link}"
       style="background-color: #6c63ff; color: #ffffff; padding: 12px 32px;
              text-decoration: none; border-radius: 6px; font-weight: bold;">
      Reset Password
    </a>
  </p>
  <p style="color: #666; font-size: 13px;">If you didn't request this, you can safely ignore this email.</p>
</body>
</html>"""
    await send_email(to, "Reset your FraudVault password", html)


async def send_verification_email(to: str, token: str) -> None:
    settings = get_settings()
    verify_link = f"{settings.app_url}/#/verify-email?token={token}"
    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1a1a2e;">Verify Your Email</h2>
  <p>Thanks for signing up for FraudVault. Please verify your email address to get started.</p>
  <p style="text-align: center; margin: 32px 0;">
    <a href="{verify_link}"
       style="background-color: #6c63ff; color: #ffffff; padding: 12px 32px;
              text-decoration: none; border-radius: 6px; font-weight: bold;">
      Verify Email
    </a>
  </p>
  <p style="color: #666; font-size: 13px;">This link expires in 24 hours.</p>
</body>
</html>"""
    await send_email(to, "Verify your FraudVault email", html)


async def send_invite_email(to: str, org_name: str, token: str) -> None:
    settings = get_settings()
    accept_link = f"{settings.app_url}/#/accept-invite?token={token}"
    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1a1a2e;">You've Been Invited</h2>
  <p>You've been invited to join <strong>{org_name}</strong> on FraudVault.</p>
  <p>Click below to accept the invitation and set up your account.</p>
  <p style="text-align: center; margin: 32px 0;">
    <a href="{accept_link}"
       style="background-color: #6c63ff; color: #ffffff; padding: 12px 32px;
              text-decoration: none; border-radius: 6px; font-weight: bold;">
      Accept Invitation
    </a>
  </p>
  <p style="color: #666; font-size: 13px;">If you weren't expecting this invitation, you can safely ignore this email.</p>
</body>
</html>"""
    await send_email(to, f"You're invited to {org_name} on FraudVault", html)
