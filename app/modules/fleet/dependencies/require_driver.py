from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user
from app.models.user import User
from app.modules.fleet.models.driver import Driver


async def require_driver(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Driver:
    if getattr(current_user, "role_name", None) != "driver":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver access only")

    result = await db.execute(
        select(Driver)
        .options(selectinload(Driver.vehicle), selectinload(Driver.payout_account))
        .where(Driver.user_id == current_user.id, Driver.deleted_at.is_(None))
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found")
    return driver
