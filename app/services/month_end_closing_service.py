import uuid
from typing import Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.month_end_closing import MonthEndClosing
from app.models.user import User
from app.models.franchise import Franchise
from app.schemas.month_end_closing import MonthEndClosingCreate, MonthEndClosingUpdateStatus
from app.services.notification_service import create_notification


async def submit_month_end_closing(
    db: AsyncSession,
    data: MonthEndClosingCreate,
    current_user: User
) -> MonthEndClosing:
    
    # Resolve the franchise ID (either from franchise owner or employee)
    resolved_franchise_id = current_user.franchise_id
    if not resolved_franchise_id:
        franchise_res = await db.execute(
            select(Franchise.id).where(Franchise.user_id == current_user.id)
        )
        resolved_franchise_id = franchise_res.scalar_one_or_none()

    # Ensure the user has a franchise
    if not resolved_franchise_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any franchise."
        )

    # Check if a pending submission with the same transaction ID already exists
    existing_txn = await db.execute(
        select(MonthEndClosing).where(MonthEndClosing.transaction_id == data.transaction_id)
    )
    if existing_txn.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A payment submission with this transaction ID already exists."
        )

    closing = MonthEndClosing(
        id=str(uuid.uuid4()),
        franchise_id=resolved_franchise_id,
        transaction_id=data.transaction_id,
        bank_name=data.bank_name,
        bank_owner_name=data.bank_owner_name,
        bank_account_number=data.bank_account_number,
        status="pending"
    )

    db.add(closing)
    await db.commit()
    await db.refresh(closing)

    # Trigger success notification to the franchise user
    await create_notification(
        db=db,
        title="Payment Submitted",
        message="Form submission has been sent successfully.",
        type="month_end_closing"
    )

    return closing


async def get_month_end_closings(
    db: AsyncSession,
    current_user: User,
    franchise_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    size: int = 20
) -> dict:
    
    query = select(MonthEndClosing)
    
    # Resolve franchise ID
    resolved_franchise_id = current_user.franchise_id
    if not resolved_franchise_id:
        franchise_res = await db.execute(
            select(Franchise.id).where(Franchise.user_id == current_user.id)
        )
        resolved_franchise_id = franchise_res.scalar_one_or_none()
    
    # If franchise user, limit to their own franchise
    if resolved_franchise_id:
        query = query.where(MonthEndClosing.franchise_id == resolved_franchise_id)
    elif franchise_id: # For super admin filtering
        query = query.where(MonthEndClosing.franchise_id == franchise_id)
        
    if status_filter:
        query = query.where(MonthEndClosing.status == status_filter)
        
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Pagination & Ordering
    query = query.order_by(desc(MonthEndClosing.created_at))
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return {
        "data": records,
        "total": total,
        "page": page,
        "size": size
    }


async def update_month_end_closing_status(
    db: AsyncSession,
    closing_id: str,
    data: MonthEndClosingUpdateStatus,
    current_user: User
) -> MonthEndClosing:
    
    result = await db.execute(
        select(MonthEndClosing).where(MonthEndClosing.id == closing_id)
    )
    closing = result.scalar_one_or_none()
    
    if not closing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Month-end closing record not found."
        )
        
    if closing.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Record is already {closing.status}."
        )

    if data.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved' or 'rejected'."
        )

    closing.status = data.status
    closing.admin_notes = data.admin_notes

    await db.commit()
    await db.refresh(closing)
    
    if data.status == "approved":
        # Send final confirmation notification
        await create_notification(
            db=db,
            title="Payment Approved",
            message="Your payment for this month has been received successfully.",
            type="month_end_closing"
        )
    elif data.status == "rejected":
        await create_notification(
            db=db,
            title="Payment Rejected",
            message="Your month-end payment submission was rejected. Please contact support.",
            type="month_end_closing"
        )
        
    return closing
