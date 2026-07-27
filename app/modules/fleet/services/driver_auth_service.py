from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.schemas.trip_sheet_driver import DriverAuthResponse, ResetPasswordRequest
from app.services.otp_service import send_otp, verify_otp
from app.utils.jwt import create_access_token


async def driver_verify_otp_login(db: AsyncSession, phone: str, otp: str) -> DriverAuthResponse:
    await verify_otp(phone, otp, "login")
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver account not found")
    driver = (
        await db.execute(select(Driver).where(Driver.user_id == user.id, Driver.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a driver account")
    token = create_access_token(
        {
            "user_id": user.id,
            "email": user.email,
            "driver_id": driver.id,
            "role": "driver",
        }
    )
    return DriverAuthResponse(token=token, userId=user.id, driverId=driver.id)


async def resend_driver_otp(phone: str) -> dict:
    await send_otp(phone, "login", via="sms")
    from app.core.config import settings
    return {"message": f"OTP sent to {phone}", "expires_in": settings.OTP_EXPIRE_MINUTES * 60}


async def forgot_password_request(email: str) -> dict:
    await send_otp(email, "password_reset", via="email")
    return {"success": True, "message": "Password reset OTP sent to your email."}


async def reset_password_with_otp(db: AsyncSession, payload: ResetPasswordRequest) -> dict:
    await verify_otp(payload.email, payload.otp, "password_reset")
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = get_password_hash(payload.newPassword)
    await db.flush()
    return {"success": True, "message": "Password reset successfully."}
