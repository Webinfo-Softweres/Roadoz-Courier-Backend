"""
Role-based Fleet Management Routes
  - DELETE /fleet/drivers/{driver_id}        — soft-delete a driver
  - PATCH  /fleet/drivers/{driver_id}        — update driver fields
  - GET    /fleet/vehicles                   — list vehicles (paginated, filtered)
  - GET    /fleet/vehicles/{vehicle_id}      — get vehicle detail
  - PATCH  /fleet/vehicles/{vehicle_id}      — update vehicle
  - DELETE /fleet/vehicles/{vehicle_id}      — soft-delete vehicle

Access:
  admin  → all records globally
  warehouse → all records (warehouse-scoped drivers use franchise)
  franchise → only their own drivers / vehicles
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User

router = APIRouter(tags=["Fleet Management"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class DriverUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[date] = None
    status: Optional[str] = None


class DriverOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    dob: Optional[date] = None
    onboarding_status: str
    status: str
    franchise_id: Optional[str] = None

    model_config = {"from_attributes": True}


class VehicleOut(BaseModel):
    id: str
    franchise_id: Optional[str] = None
    type: str
    plate_number: str
    make: str
    model: str
    year: str
    color: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class VehicleUpdateRequest(BaseModel):
    type: Optional[str] = None
    plate_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None


class VehicleListResponse(BaseModel):
    items: List[VehicleOut]
    total: int
    page: int
    limit: int
    pages: int


# ─── Driver Endpoints ──────────────────────────────────────────────────────────

@router.patch("/fleet/drivers/{driver_id}", response_model=DriverOut)
async def update_driver_endpoint(
    driver_id: str,
    payload: DriverUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("fleet:drivers:view")),
):
    """
    Update driver details (name, phone, dob, status).
    Admin sees all; franchise user only sees their own drivers.
    """
    from app.modules.fleet.services.fleet_management_service import update_driver
    return await update_driver(db, current_user, driver_id, payload.model_dump(exclude_none=True))


@router.delete("/fleet/drivers/{driver_id}", status_code=204)
async def delete_driver_endpoint(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Soft-delete a driver (sets deleted_at, deactivates their user account).
    Admin sees all; franchise user only affects their own drivers.
    """
    from app.modules.fleet.services.fleet_management_service import delete_driver
    await delete_driver(db, current_user, driver_id)
    await db.commit()


# ─── Vehicle Endpoints ─────────────────────────────────────────────────────────

@router.get("/fleet/vehicles", response_model=VehicleListResponse)
async def list_vehicles_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    plate_number: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None, alias="type"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("fleet:drivers:view")),
):
    """
    List vehicles with optional filters: plate_number, model, type, status.
    Admin sees all; franchise user sees only their franchise vehicles.
    """
    from app.modules.fleet.services.fleet_management_service import list_vehicles
    result = await list_vehicles(
        db, current_user, page, limit, plate_number, model, vehicle_type, status_filter
    )
    return result


@router.get("/fleet/vehicles/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle_endpoint(
    vehicle_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("fleet:drivers:view")),
):
    """
    Get a single vehicle detail.
    Admin sees all; franchise user only sees their own franchise vehicles.
    """
    from app.modules.fleet.services.fleet_management_service import get_vehicle
    return await get_vehicle(db, current_user, vehicle_id)


@router.patch("/fleet/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle_endpoint(
    vehicle_id: str,
    payload: VehicleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("fleet:drivers:view")),
):
    """
    Update vehicle details (plate_number, type, make, model, year, color, status).
    Admin sees all; franchise user only edits their own franchise vehicles.
    """
    from app.modules.fleet.services.fleet_management_service import update_vehicle
    return await update_vehicle(db, current_user, vehicle_id, payload.model_dump(exclude_none=True))


@router.delete("/fleet/vehicles/{vehicle_id}", status_code=204)
async def delete_vehicle_endpoint(
    vehicle_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Soft-delete a vehicle.
    Admin sees all; franchise user only affects their own franchise vehicles.
    """
    from app.modules.fleet.services.fleet_management_service import delete_vehicle
    await delete_vehicle(db, current_user, vehicle_id)
    await db.commit()
