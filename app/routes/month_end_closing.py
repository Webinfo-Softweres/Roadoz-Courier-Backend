from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.schemas.month_end_closing import (
    MonthEndClosingCreate,
    MonthEndClosingResponse,
    MonthEndClosingUpdateStatus,
    MonthEndClosingList
)
from app.services.month_end_closing_service import (
    submit_month_end_closing,
    get_month_end_closings,
    update_month_end_closing_status
)
from app.dependencies.role_checker import get_current_user, require_permission

router = APIRouter(prefix="/month-end-closings", tags=["Month End Closing"])


@router.post("/", response_model=MonthEndClosingResponse, status_code=status.HTTP_201_CREATED)
async def create_submission_endpoint(
    data: MonthEndClosingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("month_end_closing:submit"))
):
    """
    Franchise submits a month-end closing payment.
    """
    return await submit_month_end_closing(db, data, current_user)


@router.get("/", response_model=MonthEndClosingList)
async def list_submissions_endpoint(
    franchise_id: Optional[str] = Query(None, description="Filter by franchise (Super Admin only)"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("month_end_closing:view"))
):
    """
    List month-end closing payments.
    Franchises will only see their own. Super Admins can see all.
    """
    return await get_month_end_closings(db, current_user, franchise_id, status_filter, page, size)


@router.put("/{closing_id}/approve", response_model=MonthEndClosingResponse)
async def update_status_endpoint(
    closing_id: str,
    data: MonthEndClosingUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("month_end_closing:approve"))
):
    """
    Super Admin approves or rejects a month-end closing payment.
    """
    return await update_month_end_closing_status(db, closing_id, data, current_user)
