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


async def send_assignment_otp_email(
    to_email: str,
    customer_name: str,
    order_number: str,
    assignment_type: str,  # "Pickup" or "Delivery"
    otp: str,
) -> bool:
    """
    Send a formatted OTP email for pickup or delivery assignment confirmation.
    The OTP must be verified by the recipient to complete the assignment.
    """
    color_map = {"Pickup": "#e67e22", "Delivery": "#27ae60"}
    icon_map = {"Pickup": "📦", "Delivery": "🚚"}
    accent = color_map.get(assignment_type, "#007bff")
    icon = icon_map.get(assignment_type, "📋")

    subject = f"{icon} {assignment_type} OTP – Order {order_number} | Roadoz Courier"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 620px; margin: 0 auto; background: #f9f9f9; padding: 20px;">
        <div style="background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
            <!-- Header -->
            <div style="background: {accent}; padding: 28px 30px; text-align: center;">
                <h1 style="color: #fff; margin: 0; font-size: 22px; letter-spacing: 1px;">
                    {icon} Roadoz Courier
                </h1>
                <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0; font-size: 14px;">
                    {assignment_type} Assignment Confirmation
                </p>
            </div>
            <!-- Body -->
            <div style="padding: 30px;">
                <p style="color: #333; font-size: 15px;">Dear <strong>{customer_name}</strong>,</p>
                <p style="color: #555; font-size: 14px; line-height: 1.6;">
                    A <strong>{assignment_type.lower()}</strong> has been scheduled for your order
                    <strong style="color: {accent};">{order_number}</strong>.
                    Please share the OTP below with our delivery personnel to confirm the {assignment_type.lower()}.
                </p>

                <!-- OTP Box -->
                <div style="background: #f4f4f4; border: 2px dashed {accent}; border-radius: 10px;
                            padding: 24px; text-align: center; margin: 24px 0;">
                    <p style="color: #888; font-size: 13px; margin: 0 0 10px;">Your {assignment_type} OTP</p>
                    <h1 style="color: {accent}; letter-spacing: 12px; margin: 0; font-size: 40px;">
                        {otp}
                    </h1>
                </div>

                <p style="color: #e74c3c; font-size: 13px; margin: 0 0 16px;">
                    ⏰ This OTP expires in <strong>{settings.OTP__MINUTES} minutes</strong>.
                </p>
                <p style="color: #777; font-size: 13px; line-height: 1.6;">
                    <strong>Do not share</strong> this OTP with anyone other than the verified Roadoz Courier personnel at your door.
                    If you did not request this, please contact our support immediately.
                </p>
            </div>
            <!-- Footer -->
            <div style="background: #f4f4f4; padding: 16px 30px; text-align: center; border-top: 1px solid #eee;">
                <p style="color: #aaa; font-size: 12px; margin: 0;">
                    &copy; Roadoz Courier — This is an automated message. Please do not reply.
                </p>
            </div>
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

        logger.info(f"Assignment OTP email ({assignment_type}) sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send assignment OTP email: {e}")
        return False

