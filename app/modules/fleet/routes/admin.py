from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.role_checker import require_permission
from app.models.user import User
from app.modules.fleet.schemas.admin import (
    ApproveDriverRequest,
    DriverDetailOut,
    DriverListResponse,
    RejectDriverRequest,
)
from app.modules.fleet.services.driver_service import (
    approve_driver,
    get_driver_detail,
    list_drivers,
    reject_driver,
)

router = APIRouter(tags=["Fleet Admin"])


@router.get("/drivers", response_model=DriverListResponse)
async def get_drivers(
    onboarding_status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("fleet:drivers:view")),
    db: AsyncSession = Depends(get_db),
):
    return await list_drivers(db, current_user, onboarding_status=onboarding_status, skip=skip, limit=limit)


@router.get("/drivers/{driver_id}", response_model=DriverDetailOut)
async def get_driver(
    driver_id: str,
    current_user: User = Depends(require_permission("fleet:drivers:view")),
    db: AsyncSession = Depends(get_db),
):
    return await get_driver_detail(db, current_user, driver_id)


@router.post("/drivers/{driver_id}/approve", response_model=DriverDetailOut)
async def approve(
    driver_id: str,
    current_user: User = Depends(require_permission("fleet:drivers:approve")),
    db: AsyncSession = Depends(get_db),
):
    await approve_driver(db, current_user, driver_id)
    return await get_driver_detail(db, current_user, driver_id)


@router.post("/drivers/{driver_id}/reject", response_model=DriverDetailOut)
async def reject(
    driver_id: str,
    payload: RejectDriverRequest,
    current_user: User = Depends(require_permission("fleet:drivers:approve")),
    db: AsyncSession = Depends(get_db),
):
    await reject_driver(db, current_user, driver_id, payload.rejection_reason)
    return await get_driver_detail(db, current_user, driver_id)
