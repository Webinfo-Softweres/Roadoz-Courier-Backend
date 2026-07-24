"""
Fleet management service — role-based CRUD for Drivers and Vehicles.

Access rules:
  - Admin       (franchise_id=None, warehouse_id=None) → full global access, no scope filter
  - Warehouse   (warehouse_id is set)                  → sees ONLY own warehouse drivers/vehicles,
                                                          new drivers/vehicles auto-pinned to their warehouse
  - Franchise   (franchise_id is set)                  → sees ONLY own franchise drivers/vehicles,
                                                          new drivers/vehicles auto-pinned to their franchise
"""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.franchise import Franchise
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.payout_account import DriverPayoutAccount
from app.modules.fleet.models.vehicle import Vehicle


# ─── Role Helpers ─────────────────────────────────────────────────────────────

async def _resolve_franchise_id(db: AsyncSession, user: User) -> Optional[str]:
    """Return franchise_id if the caller is a franchise user, else None."""
    # 1. Direct franchise binding on user
    if getattr(user, "franchise_id", None):
        return user.franchise_id
        
    # 2. User is a franchise owner
    franchise = (
        await db.execute(select(Franchise).where(Franchise.user_id == user.id))
    ).scalars().first()
    if franchise:
        return franchise.id
        
    return None


async def _resolve_warehouse_id(db: AsyncSession, user: User) -> Optional[str]:
    from app.services.order_service import _resolve_warehouse_id as _wh
    return await _wh(db, user)


def _is_admin(franchise_id: Optional[str], warehouse_id: Optional[str]) -> bool:
    """True only when the caller has neither a franchise nor a warehouse binding."""
    return not franchise_id and not warehouse_id


def _apply_driver_scope(query, franchise_id: Optional[str], warehouse_id: Optional[str]):
    """
    Append the correct WHERE clause for drivers based on caller's role.
      - Admin      → no extra filter (sees everything)
      - Warehouse  → filter to own warehouse_id
      - Franchise  → filter to own franchise_id
    """
    if warehouse_id:
        query = query.where(Driver.warehouse_id == warehouse_id)
    elif franchise_id:
        query = query.where(Driver.franchise_id == franchise_id)
    return query


def _apply_vehicle_scope(query, franchise_id: Optional[str], warehouse_id: Optional[str]):
    """
    Append the correct WHERE clause for vehicles based on caller's role.
      - Admin      → no extra filter
      - Warehouse  → filter to own warehouse_id
      - Franchise  → filter to own franchise_id
    """
    if warehouse_id:
        query = query.where(Vehicle.warehouse_id == warehouse_id)
    elif franchise_id:
        query = query.where(Vehicle.franchise_id == franchise_id)
    return query


# ─── Driver Role ───────────────────────────────────────────────────────────────

async def _get_driver_role(db: AsyncSession) -> Role:
    result = await db.execute(
        select(Role).where(
            Role.name == "driver",
            Role.franchise_id.is_(None),
            Role.warehouse_id.is_(None),
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Driver role is not configured",
        )
    return role


# ─── Driver CRUD ───────────────────────────────────────────────────────────────

async def create_driver(
    db: AsyncSession,
    current_user: User,
    payload: dict,
) -> Driver:
    """
    Create a new driver user + driver record.
    - Franchise user → driver.franchise_id set to their franchise automatically.
    - Admin/Warehouse → driver.franchise_id remains None (global/unassigned).
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    # Email uniqueness check
    existing = await db.execute(select(User).where(User.email == payload["email"]))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        name=f"{payload['firstName']} {payload['lastName']}",
        email=payload["email"],
        password_hash=get_password_hash(payload["password"]),
        phone=payload["phone"],
        is_active=True,
    )
    db.add(user)
    await db.flush()

    driver = Driver(
        user_id=user.id,
        first_name=payload["firstName"],
        last_name=payload["lastName"],
        phone=payload["phone"],
        dob=payload["dob"],
        onboarding_status="incomplete",
        status="draft",
        # Pin to franchise/warehouse if applicable
        franchise_id=franchise_id if franchise_id else None,
        warehouse_id=warehouse_id if warehouse_id else None,
    )
    db.add(driver)
    await db.flush()

    role = await _get_driver_role(db)
    db.add(UserRole(user_id=user.id, role_id=role.id))

    await db.flush()
    await db.refresh(driver)
    return driver


async def update_driver(
    db: AsyncSession,
    current_user: User,
    driver_id: str,
    payload: dict,
) -> Driver:
    """
    Update driver fields.
    - Franchise user → scoped to own franchise.
    - Admin/Warehouse → sees all drivers.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))
    query = _apply_driver_scope(query, franchise_id, warehouse_id)

    driver = (await db.execute(query)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    UPDATABLE_FIELDS = {"first_name", "last_name", "phone", "dob", "status"}
    for field, value in payload.items():
        if field in UPDATABLE_FIELDS and value is not None:
            setattr(driver, field, value)

    await db.flush()
    await db.refresh(driver)
    return driver


async def delete_driver(
    db: AsyncSession,
    current_user: User,
    driver_id: str,
) -> None:
    """
    Soft-delete a driver (sets deleted_at, deactivates the user account).
    - Franchise user → scoped to own franchise.
    - Admin/Warehouse → can delete any driver.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))
    query = _apply_driver_scope(query, franchise_id, warehouse_id)

    driver = (await db.execute(query)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    driver.deleted_at = datetime.utcnow()
    if driver.user:
        driver.user.is_active = False

    await db.flush()


async def upload_document(
    db: AsyncSession,
    current_user: User,
    driver_id: str,
    document_type: str,
    file: UploadFile,
) -> str:
    """
    Upload a document for a driver.
    - Franchise user → can only upload for drivers in their franchise.
    - Admin/Warehouse → can upload for any driver.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))
    query = _apply_driver_scope(query, franchise_id, warehouse_id)

    driver = (await db.execute(query)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    from app.modules.fleet.services.file_service import upload_driver_document
    return await upload_driver_document(db, driver, document_type, file)


async def create_bank_details(
    db: AsyncSession,
    current_user: User,
    driver_id: str,
    payload: dict,
) -> None:
    """
    Save bank/payout details for a driver and mark as pending_verification.
    - Franchise user → can only act on drivers in their franchise.
    - Admin/Warehouse → can act on any driver.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    # Scope-aware driver lookup
    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))
    query = _apply_driver_scope(query, franchise_id, warehouse_id)

    driver = (await db.execute(query)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    # Load with payout relationship
    from sqlalchemy.orm import selectinload
    driver_full = (await db.execute(
        select(Driver)
        .options(selectinload(Driver.payout_account))
        .where(Driver.id == driver_id)
    )).scalar_one()

    if driver_full.payout_account:
        payout = driver_full.payout_account
        # Only update fields that are actually provided (partial update support)
        if "accountHolderName" in payload:
            payout.account_holder_name  = payload["accountHolderName"]
        if "bankName" in payload:
            payout.bank_name            = payload["bankName"]
        if "accountNumber" in payload:
            payout.account_number       = payload["accountNumber"]
        if "ifscOrRoutingCode" in payload:
            payout.ifsc_or_routing_code = payload["ifscOrRoutingCode"]
    else:
        # Creating new payout account — all fields required
        required = {"accountHolderName", "bankName", "accountNumber", "ifscOrRoutingCode"}
        missing = required - payload.keys()
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required bank fields: {', '.join(sorted(missing))}",
            )
        db.add(DriverPayoutAccount(
            driver_id=driver.id,
            account_holder_name=payload["accountHolderName"],
            bank_name=payload["bankName"],
            account_number=payload["accountNumber"],
            ifsc_or_routing_code=payload["ifscOrRoutingCode"],
        ))

    # Mark driver ready for approval
    driver_full.onboarding_status = "pending_verification"
    driver_full.submitted_at      = datetime.utcnow()
    driver_full.rejection_reason  = None

    await db.flush()


# ─── Vehicle CRUD ─────────────────────────────────────────────────────────────

async def create_vehicle(
    db: AsyncSession,
    current_user: User,
    payload: dict,
) -> Vehicle:
    """
    Create a standalone vehicle record.
    - Franchise user → vehicle.franchise_id auto-set to their franchise.
    - Admin/Warehouse → vehicle.franchise_id remains None (global/unassigned).
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    from app.modules.fleet.schemas.onboard import VehicleRequest
    req = VehicleRequest(**payload)

    vehicle = Vehicle(
        id=str(uuid.uuid4()),
        type=req.vehicleType,
        plate_number=req.registrationNumber,
        make=req.make,
        model=req.model,
        year=req.year,
        color=req.color,
        status="available",
        # Pin to franchise/warehouse if applicable
        franchise_id=franchise_id if franchise_id else None,
        warehouse_id=warehouse_id if warehouse_id else None,
    )
    db.add(vehicle)
    await db.flush()
    await db.refresh(vehicle)
    return vehicle


async def get_vehicle(
    db: AsyncSession,
    current_user: User,
    vehicle_id: str,
) -> Vehicle:
    """
    Get a single vehicle.
    - Franchise user → scoped to own franchise.
    - Admin/Warehouse → any vehicle.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
    query = _apply_vehicle_scope(query, franchise_id, warehouse_id)

    vehicle = (await db.execute(query)).scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


async def list_vehicles(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    limit: int = 20,
    plate_number: Optional[str] = None,
    model: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> dict:
    """
    List vehicles with pagination and optional filters.
    - Franchise user → scoped to own franchise.
    - Admin/Warehouse → all vehicles globally.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    filters = [Vehicle.deleted_at.is_(None)]

    # Role-based scope filter
    if warehouse_id:
        filters.append(Vehicle.warehouse_id == warehouse_id)
    elif franchise_id:
        filters.append(Vehicle.franchise_id == franchise_id)

    # Optional search filters
    if plate_number:
        filters.append(Vehicle.plate_number.ilike(f"%{plate_number}%"))
    if model:
        filters.append(Vehicle.model.ilike(f"%{model}%"))
    if vehicle_type:
        filters.append(Vehicle.type.ilike(f"%{vehicle_type}%"))
    if status_filter:
        filters.append(Vehicle.status == status_filter)

    total = (
        await db.execute(
            select(func.count()).select_from(Vehicle).where(and_(*filters))
        )
    ).scalar() or 0

    rows = (
        await db.execute(
            select(Vehicle)
            .where(and_(*filters))
            .order_by(Vehicle.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).scalars().all()

    return {
        "items": rows,
        "total": total,
        "page":  page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
    }


async def update_vehicle(
    db: AsyncSession,
    current_user: User,
    vehicle_id: str,
    payload: dict,
) -> Vehicle:
    """
    Update vehicle fields.
    - Franchise user → scoped to own franchise.
    - Admin/Warehouse → any vehicle.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
    query = _apply_vehicle_scope(query, franchise_id, warehouse_id)

    vehicle = (await db.execute(query)).scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    UPDATABLE_FIELDS = {"type", "plate_number", "make", "model", "year", "color", "status"}
    for field, value in payload.items():
        if field in UPDATABLE_FIELDS and value is not None:
            setattr(vehicle, field, value)

    await db.flush()
    await db.refresh(vehicle)
    return vehicle


async def delete_vehicle(
    db: AsyncSession,
    current_user: User,
    vehicle_id: str,
) -> None:
    """
    Soft-delete a vehicle.
    - Franchise user → scoped to own franchise.
    - Admin/Warehouse → any vehicle.
    """
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
    query = _apply_vehicle_scope(query, franchise_id, warehouse_id)

    vehicle = (await db.execute(query)).scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    vehicle.deleted_at = datetime.utcnow()
    await db.flush()
