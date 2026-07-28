import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_email_otp(to_email: str, otp: str, purpose: str = "login") -> bool:
    """Send OTP via SMTP email."""
    purpose_map = {
        "login": "Login Verification",
        "password_reset": "Password Reset",
        "franchise_auth": "Franchise Authentication",
    }
    subject = f"OTP for {purpose_map.get(purpose, 'Verification')}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #f4f4f4; padding: 30px; border-radius: 8px;">
            <h2 style="color: #333;">Your OTP Code</h2>
            <p style="color: #666;">Use the following OTP for <strong>{purpose_map.get(purpose, 'verification')}</strong>:</p>
            <div style="background: #fff; border: 2px dashed #007bff; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                <h1 style="color: #007bff; letter-spacing: 8px; margin: 0;">{otp}</h1>
            </div>
            <p style="color: #999; font-size: 12px;">
                This OTP expires in {settings.OTP_EXPIRE_MINUTES} minutes. Do not share it with anyone.
            </p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], to_email, msg.as_string())

        logger.info(f"OTP email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email OTP: {e}")
        return False

async def send_email(to_email: str, subject: str, body: str, reply_to: str = None) -> bool:
    """Send generic email via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME
        msg["To"] = to_email
        
        if reply_to:
            msg["Reply-To"] = reply_to
            
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
