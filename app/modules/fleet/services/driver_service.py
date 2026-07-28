from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.fleet_file import FleetFile
from app.modules.fleet.models.payout_account import DriverPayoutAccount
from app.modules.fleet.schemas.admin import ApproveDriverRequest, DriverDetailOut, DriverListItem, DriverListResponse
from app.modules.fleet.services.file_service import ALLOWED_DOCUMENT_TYPES


async def get_driver_by_id(db: AsyncSession, current_user: User, driver_id: str) -> Driver | None:
    from app.modules.fleet.services.fleet_management_service import _resolve_franchise_id, _resolve_warehouse_id, _apply_driver_scope
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = (
        select(Driver)
        .options(
            selectinload(Driver.vehicle),
            selectinload(Driver.payout_account),
            selectinload(Driver.user),
        )
        .where(Driver.id == driver_id, Driver.deleted_at.is_(None))
    )
    query = _apply_driver_scope(query, franchise_id, warehouse_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_drivers(
    db: AsyncSession,
    current_user: User,
    onboarding_status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> DriverListResponse:
    query = (
        select(Driver, User.email)
        .join(User, User.id == Driver.user_id)
        .where(Driver.deleted_at.is_(None))
    )
    count_query = select(func.count()).select_from(Driver).where(Driver.deleted_at.is_(None))

    from app.modules.fleet.services.fleet_management_service import _resolve_franchise_id, _resolve_warehouse_id, _apply_driver_scope
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = _apply_driver_scope(query, franchise_id, warehouse_id)
    count_query = _apply_driver_scope(count_query, franchise_id, warehouse_id)
    
    query = query.order_by(Driver.created_at.desc())

    if onboarding_status:
        query = query.where(Driver.onboarding_status == onboarding_status)
        count_query = count_query.where(Driver.onboarding_status == onboarding_status)

    total = (await db.execute(count_query)).scalar_one()
    rows = (await db.execute(query.offset(skip).limit(limit))).all()

    items = [
        DriverListItem(
            id=driver.id,
            first_name=driver.first_name,
            last_name=driver.last_name,
            email=email,
            phone=driver.phone,
            onboarding_status=driver.onboarding_status,
            status=driver.status,
            submitted_at=driver.submitted_at,
            created_at=driver.created_at,
        )
        for driver, email in rows
    ]
    return DriverListResponse(items=items, total=total)


async def get_driver_detail(db: AsyncSession, current_user: User, driver_id: str) -> DriverDetailOut:
    driver = await get_driver_by_id(db, current_user, driver_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    docs_result = await db.execute(
        select(FleetFile).where(FleetFile.subject_type == "driver", FleetFile.subject_id == driver.id)
    )
    documents = list(docs_result.scalars().all())

    return DriverDetailOut(
        id=driver.id,
        first_name=driver.first_name,
        last_name=driver.last_name,
        email=driver.user.email,
        phone=driver.phone,
        dob=driver.dob,
        onboarding_status=driver.onboarding_status,
        status=driver.status,
        franchise_id=driver.franchise_id,
        submitted_at=driver.submitted_at,
        rejection_reason=driver.rejection_reason,
        vehicle=driver.vehicle,
        documents=documents,
        payout_account=driver.payout_account,
    )


async def approve_driver(
    db: AsyncSession,
    current_user: User,
    driver_id: str,
    payload: ApproveDriverRequest | None = None,
) -> Driver:
    driver = await get_driver_by_id(db, current_user, driver_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    if driver.onboarding_status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not pending verification",
        )

    from app.modules.fleet.services.fleet_management_service import _resolve_franchise_id, _resolve_warehouse_id
    caller_franchise_id = await _resolve_franchise_id(db, current_user)
    caller_warehouse_id = await _resolve_warehouse_id(db, current_user)

    franchise_id = None
    warehouse_id = None

    # ── Assignment resolution ──────────────────────────────────────────────────
    # Rule 1: If the driver already has an assignment (created via web dashboard),
    #         ALWAYS keep it — no one can override it through the approval payload.
    if driver.franchise_id or driver.warehouse_id:
        franchise_id = driver.franchise_id
        warehouse_id = driver.warehouse_id

    # Rule 2: Driver has NO assignment (registered via mobile app).
    #         The approver's own scope takes priority over the payload.
    elif caller_warehouse_id:
        # Warehouse user approving → assign to their warehouse
        warehouse_id = caller_warehouse_id
        franchise_id = None
    elif caller_franchise_id:
        # Franchise user approving → assign to their franchise
        franchise_id = caller_franchise_id
        warehouse_id = None
    elif payload and payload.warehouse_id:
        warehouse_id = payload.warehouse_id
        franchise_id = payload.franchise_id
    elif payload and payload.franchise_id:
        franchise_id = payload.franchise_id
        warehouse_id = None
    # else: Admin approving unassigned driver with no payload — leave unassigned

    driver.onboarding_status = "approved"
    driver.status = "active"
    driver.franchise_id = franchise_id
    driver.warehouse_id = warehouse_id
    driver.rejection_reason = None

    if driver.vehicle:
        driver.vehicle.franchise_id = franchise_id
        driver.vehicle.warehouse_id = warehouse_id
        driver.vehicle.status = "available"

    if driver.user:
        driver.user.is_active = True

    await db.flush()
    return driver


async def reject_driver(db: AsyncSession, current_user: User, driver_id: str, rejection_reason: str) -> Driver:
    driver = await get_driver_by_id(db, current_user, driver_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    if driver.onboarding_status != "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not pending verification",
        )

    driver.onboarding_status = "rejected"
    driver.status = "draft"
    driver.rejection_reason = rejection_reason
    driver.submitted_at = None

    payout = driver.payout_account
    if payout:
        await db.delete(payout)

    await db.flush()
    return driver


def documents_complete(documents: list[FleetFile]) -> bool:
    uploaded = {d.document_type for d in documents}
    return ALLOWED_DOCUMENT_TYPES.issubset(uploaded)
