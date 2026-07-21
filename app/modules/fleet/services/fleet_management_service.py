"""
Fleet management service — role-based CRUD for Drivers and Vehicles.

Access rules:
  - Admin (no franchise_id, no warehouse_id): full global access
  - Warehouse user: access to drivers/vehicles belonging to their warehouse franchise (drivers
    are franchise-scoped, so warehouse sees all)
  - Franchise user: access only to drivers/vehicles belonging to their franchise
"""

import math
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.franchise import Franchise
from app.models.user import User
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.vehicle import Vehicle


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _resolve_franchise_id(db: AsyncSession, user: User) -> Optional[str]:
    """Return the franchise_id for a franchise user, else None."""
    if getattr(user, "franchise_id", None):
        return user.franchise_id
    franchise = (
        await db.execute(select(Franchise).where(Franchise.user_id == user.id))
    ).scalars().first()
    return franchise.id if franchise else None


async def _resolve_warehouse_id(db: AsyncSession, user: User) -> Optional[str]:
    from app.services.order_service import _resolve_warehouse_id as _wh
    return await _wh(db, user)


def _is_admin(franchise_id: Optional[str], warehouse_id: Optional[str]) -> bool:
    return not franchise_id and not warehouse_id


# ─── Driver CRUD ───────────────────────────────────────────────────────────────

async def update_driver(
    db: AsyncSession,
    current_user: User,
    driver_id: str,
    payload: dict,
) -> Driver:
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))

    # Scope to franchise if not admin
    if not _is_admin(franchise_id, warehouse_id):
        if franchise_id:
            query = query.where(Driver.franchise_id == franchise_id)
        # warehouse sees all drivers (same scope)

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
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))

    if not _is_admin(franchise_id, warehouse_id):
        if franchise_id:
            query = query.where(Driver.franchise_id == franchise_id)

    driver = (await db.execute(query)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    driver.deleted_at = datetime.utcnow()
    if driver.user:
        driver.user.is_active = False

    await db.flush()


# ─── Vehicle CRUD ─────────────────────────────────────────────────────────────

async def get_vehicle(
    db: AsyncSession,
    current_user: User,
    vehicle_id: str,
) -> Vehicle:
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))

    if not _is_admin(franchise_id, warehouse_id):
        if franchise_id:
            query = query.where(Vehicle.franchise_id == franchise_id)

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
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    filters = [Vehicle.deleted_at.is_(None)]

    if not _is_admin(franchise_id, warehouse_id):
        if franchise_id:
            filters.append(Vehicle.franchise_id == franchise_id)

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
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
    }


async def update_vehicle(
    db: AsyncSession,
    current_user: User,
    vehicle_id: str,
    payload: dict,
) -> Vehicle:
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))

    if not _is_admin(franchise_id, warehouse_id):
        if franchise_id:
            query = query.where(Vehicle.franchise_id == franchise_id)

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
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))

    if not _is_admin(franchise_id, warehouse_id):
        if franchise_id:
            query = query.where(Vehicle.franchise_id == franchise_id)

    vehicle = (await db.execute(query)).scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    vehicle.deleted_at = datetime.utcnow()
    await db.flush()
