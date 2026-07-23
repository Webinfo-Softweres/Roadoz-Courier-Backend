"""
Role-based Fleet Management Routes  (Website / Admin panel)

Access matrix:
  Role        | Create Driver | Create Vehicle | Upload Doc | Bank Details | Update | Delete | List / Get
  ------------|---------------|----------------|------------|--------------|--------|--------|------------
  admin       |      ✓        |       ✓        |     ✓      |      ✓       |   ✓    |   ✓    |  all records
  warehouse   |      ✓        |       ✓        |     ✓      |      ✓       |   ✓    |   ✓    |  all records
  franchise   |      ✓        |       ✓        |     ✓      |      ✓       |   ✓    |   ✓    |  own franchise only

Role is resolved inside every handler via:
  _resolve_franchise_id  → non-None  means caller is a franchise user
  _resolve_warehouse_id  → non-None  means caller is a warehouse user
  _is_admin              → both None means caller is admin (global access)
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.modules.fleet.schemas.onboard import BankDetailsRequest, RegisterRequest, VehicleRequest

router = APIRouter(prefix="/website", tags=["Fleet Management  Website"])


# ─── Shared role helpers (imported lazily to avoid circular imports) ───────────

async def _get_role_scope(db: AsyncSession, user: User):
    """Return (franchise_id, warehouse_id, is_admin) for the caller."""
    from app.modules.fleet.services.fleet_management_service import (
        _resolve_franchise_id,
        _resolve_warehouse_id,
        _is_admin,
    )
    franchise_id  = await _resolve_franchise_id(db, user)
    warehouse_id  = await _resolve_warehouse_id(db, user)
    admin         = _is_admin(franchise_id, warehouse_id)
    return franchise_id, warehouse_id, admin


# ─── Schemas ──────────────────────────────────────────────────────────────────

class DriverUpdateRequest(BaseModel):
    # Driver details (all optional)
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    phone:      Optional[str] = None
    dob:        Optional[date] = None
    status:     Optional[str] = None
    # Bank details (all optional — only updated if at least one is provided)
    accountHolderName:  Optional[str] = None
    bankName:           Optional[str] = None
    accountNumber:      Optional[str] = None
    ifscOrRoutingCode:  Optional[str] = None


class DriverOut(BaseModel):
    id:                str
    first_name:        str
    last_name:         str
    phone:             Optional[str] = None
    dob:               Optional[date] = None
    onboarding_status: str
    status:            str
    franchise_id:      Optional[str] = None

    model_config = {"from_attributes": True}


class VehicleOut(BaseModel):
    id:           str
    franchise_id: Optional[str] = None
    type:         str
    plate_number: str
    make:         str
    model:        str
    year:         str
    color:        Optional[str] = None
    status:       str

    model_config = {"from_attributes": True}


class VehicleUpdateRequest(BaseModel):
    type:         Optional[str] = None
    plate_number: Optional[str] = None
    make:         Optional[str] = None
    model:        Optional[str] = None
    year:         Optional[str] = None
    color:        Optional[str] = None
    status:       Optional[str] = None


class VehicleListResponse(BaseModel):
    items: List[VehicleOut]
    total: int
    page:  int
    limit: int
    pages: int


# ─── Driver Endpoints ─────────────────────────────────────────────────────────

@router.post("/fleet/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
async def create_driver_endpoint(
    payload:      RegisterRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Create a new driver account.
    - Admin / Warehouse → driver created with no franchise restriction (franchise_id = None unless explicitly scoped).
    - Franchise user    → driver is automatically tied to their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import create_driver
    return await create_driver(db, current_user, payload.model_dump())


@router.patch("/fleet/drivers/{driver_id}", response_model=DriverOut)
async def update_driver_endpoint(
    driver_id:         str,
    # ── Driver basic fields (Form) ────────────────────────────
    first_name:        Optional[str]  = Form(None),
    last_name:         Optional[str]  = Form(None),
    phone:             Optional[str]  = Form(None),
    dob:               Optional[date] = Form(None),
    status:            Optional[str]  = Form(None),
    # ── Bank detail fields (Form) ─────────────────────────────
    accountHolderName: Optional[str]  = Form(None),
    bankName:          Optional[str]  = Form(None),
    accountNumber:     Optional[str]  = Form(None),
    ifscOrRoutingCode: Optional[str]  = Form(None),
    # ── Document files (all optional) ─────────────────────────
    license_front:     Optional[UploadFile] = File(None),
    license_back:      Optional[UploadFile] = File(None),
    vehicle_insurance: Optional[UploadFile] = File(None),
    # ── Auth ──────────────────────────────────────────────────
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:view")),
):
    """
    Update a driver in one call (multipart/form-data).
    All fields are optional — only provided fields are updated.
    - Driver details : first_name, last_name, phone, dob, status
    - Bank details   : accountHolderName, bankName, accountNumber, ifscOrRoutingCode
    - Documents      : license_front, license_back, vehicle_insurance (image files)
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import (
        update_driver, upload_document, create_bank_details
    )

    # 1. Update basic driver fields if any are provided
    driver_fields = {k: v for k, v in {
        "first_name": first_name,
        "last_name":  last_name,
        "phone":      phone,
        "dob":        dob,
        "status":     status,
    }.items() if v is not None}

    if driver_fields:
        driver = await update_driver(db, current_user, driver_id, driver_fields)
    else:
        # Still need the driver object for documents/bank
        from app.modules.fleet.services.fleet_management_service import _resolve_franchise_id, _resolve_warehouse_id, _apply_driver_scope
        from sqlalchemy import select as _select
        from app.modules.fleet.models.driver import Driver as _Driver
        _fid = await _resolve_franchise_id(db, current_user)
        _wid = await _resolve_warehouse_id(db, current_user)
        _q = _select(_Driver).where(_Driver.id == driver_id, _Driver.deleted_at.is_(None))
        _q = _apply_driver_scope(_q, _fid, _wid)
        driver = (await db.execute(_q)).scalar_one_or_none()
        if not driver:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Driver not found")

    # 2. Upload documents if any files are provided
    docs_to_upload = {
        "license_front":     license_front,
        "license_back":      license_back,
        "vehicle_insurance": vehicle_insurance,
    }
    for doc_type, file in docs_to_upload.items():
        if file is not None:
            await upload_document(db, current_user, driver_id, doc_type, file)

    # 3. Update bank details if any bank field is provided
    bank_fields = {k: v for k, v in {
        "accountHolderName":  accountHolderName,
        "bankName":           bankName,
        "accountNumber":      accountNumber,
        "ifscOrRoutingCode":  ifscOrRoutingCode,
    }.items() if v is not None}

    if bank_fields:
        await create_bank_details(db, current_user, driver_id, bank_fields)

    await db.commit()
    await db.refresh(driver)
    return driver


@router.delete("/fleet/drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_driver_endpoint(
    driver_id:    str,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Soft-delete a driver (sets deleted_at, deactivates their user account).
    - Admin / Warehouse → can delete any driver globally.
    - Franchise user    → can only delete drivers belonging to their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import delete_driver
    await delete_driver(db, current_user, driver_id)
    await db.commit()


# ─── Driver Document & Bank Detail Endpoints ──────────────────────────────────

@router.post("/fleet/drivers/{driver_id}/documents")
async def upload_document_endpoint(
    driver_id:    str,
    documentType: str        = Form(...),  # license_front | license_back | vehicle_insurance
    file:         UploadFile = File(...),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Upload a driver document (license_front, license_back, vehicle_insurance).
    - Admin / Warehouse → can upload for any driver.
    - Franchise user    → can only upload for drivers in their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import upload_document
    url = await upload_document(db, current_user, driver_id, documentType, file)
    return {"success": True, "documentUrl": url}


@router.post("/fleet/drivers/{driver_id}/bank-details")
async def create_bank_details_endpoint(
    driver_id:    str,
    payload:      BankDetailsRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Save bank / payout details for a driver.
    Also marks the driver as 'pending_verification' (ready to approve).
    - Admin / Warehouse → can set for any driver.
    - Franchise user    → can only set for drivers in their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import create_bank_details
    await create_bank_details(db, current_user, driver_id, payload.model_dump())
    return {"success": True, "message": "Bank details saved"}


# ─── Vehicle Endpoints ────────────────────────────────────────────────────────

@router.post("/fleet/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle_endpoint(
    payload:      VehicleRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Create a new vehicle (independent of any driver).
    - Admin / Warehouse → vehicle created globally (no franchise pinning).
    - Franchise user    → vehicle automatically pinned to their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import create_vehicle
    return await create_vehicle(db, current_user, payload.model_dump())


@router.get("/fleet/vehicles", response_model=VehicleListResponse)
async def list_vehicles_endpoint(
    page:          int            = Query(1,    ge=1),
    limit:         int            = Query(20,   ge=1, le=100),
    plate_number:  Optional[str]  = Query(None),
    model:         Optional[str]  = Query(None),
    vehicle_type:  Optional[str]  = Query(None, alias="type"),
    status_filter: Optional[str]  = Query(None, alias="status"),
    db:            AsyncSession   = Depends(get_db),
    current_user:  User           = Depends(get_current_user),
    _:             User           = Depends(require_permission("fleet:drivers:view")),
):
    """
    List vehicles (paginated + optional filters).
    - Admin / Warehouse → all vehicles globally.
    - Franchise user    → only vehicles belonging to their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import list_vehicles
    return await list_vehicles(
        db, current_user, page, limit, plate_number, model, vehicle_type, status_filter
    )


@router.get("/fleet/vehicles/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle_endpoint(
    vehicle_id:   str,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:view")),
):
    """
    Get a single vehicle's details.
    - Admin / Warehouse → any vehicle.
    - Franchise user    → only vehicles in their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import get_vehicle
    return await get_vehicle(db, current_user, vehicle_id)


@router.patch("/fleet/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle_endpoint(
    vehicle_id:   str,
    payload:      VehicleUpdateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:view")),
):
    """
    Update vehicle fields.
    - Admin / Warehouse → can update any vehicle.
    - Franchise user    → can only update vehicles in their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import update_vehicle
    return await update_vehicle(db, current_user, vehicle_id, payload.model_dump(exclude_none=True))


@router.delete("/fleet/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_endpoint(
    vehicle_id:   str,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _:            User         = Depends(require_permission("fleet:drivers:approve")),
):
    """
    Soft-delete a vehicle.
    - Admin / Warehouse → can delete any vehicle globally.
    - Franchise user    → can only delete vehicles in their franchise.
    """
    franchise_id, warehouse_id, is_admin = await _get_role_scope(db, current_user)

    from app.modules.fleet.services.fleet_management_service import delete_vehicle
    await delete_vehicle(db, current_user, vehicle_id)
    await db.commit()
