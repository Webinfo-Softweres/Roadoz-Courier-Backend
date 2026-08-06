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
    warehouse_id:      Optional[str] = None
    vehicle_id:        Optional[str] = None
    online:            bool

    model_config = {"from_attributes": True}


class DriverListResponse(BaseModel):
    items: List[DriverOut]
    total_drivers: int
    on_road_drivers: int
    page:  int
    limit: int
    pages: int


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
    _:            User         = Depends(require_permission("drivers:create")),
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
    _:            User         = Depends(require_permission("drivers:update")),
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
    _:            User         = Depends(require_permission("drivers:delete")),
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
    _:            User         = Depends(require_permission("drivers:create")),
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
    _:            User         = Depends(require_permission("drivers:create")),
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
    _:            User         = Depends(require_permission("vehicle:create")),
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
    _:             User           = Depends(require_permission("vehicle:view")),
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
    _:            User         = Depends(require_permission("vehicle:view")),
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
    _:            User         = Depends(require_permission("vehicle:update")),
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
    _:            User         = Depends(require_permission("vehicle:delete")),
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


@router.get("/fleet/drivers/{driver_id}/location")
async def get_driver_location_details(
    driver_id: str,
    current_user: User = Depends(require_permission("drivers:view")),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full location details from HERE API for a driver based on their latest synced location.
    Role-based access:
    - Admin: can query for any driver
    - Franchise: can query only for their franchise's drivers
    - Warehouse: can query only for their warehouse's drivers
    """
    from app.modules.fleet.models.driver import Driver
    from app.modules.fleet.models.driver_location import DriverLocation
    from sqlalchemy import select
    from app.services.location_service import get_full_location_from_lat_lng
    
    # 1. Check role scope
    _fid, _wid, _admin = await _get_role_scope(db, current_user)
    
    # 2. Verify driver existence and access rights
    query = select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None))
    if not _admin:
        if _fid:
            query = query.where(Driver.franchise_id == _fid)
        elif _wid:
            query = query.where(Driver.warehouse_id == _wid)
            
    driver = (await db.execute(query)).scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found or you do not have access to this driver.")
        
    # 3. Fetch latest coordinates from database
    location = (await db.execute(
        select(DriverLocation).where(DriverLocation.driver_id == driver_id)
    )).scalar_one_or_none()
    
    if not location:
        raise HTTPException(status_code=404, detail="No location data found for this driver yet.")

    # 4. Fetch location details from HERE API
    location_details = await get_full_location_from_lat_lng(location.latitude, location.longitude)
    if not location_details:
        raise HTTPException(status_code=400, detail="Could not retrieve location details from HERE API.")
        
    return location_details


@router.get("/fleet/drivers/locations")
async def list_driver_locations(
    current_user: User = Depends(require_permission("drivers:view")),
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by driver status (e.g. active, draft)"),
    online_only: bool = Query(True, description="Show only online drivers. Set to false to include all drivers."),
):
    """
    List all currently ONLINE drivers with their live location, current vehicle, and assignment status.
    By default only online drivers are returned. Set online_only=false to include offline drivers.
    Role-based access:
    - Admin : sees ALL drivers across all franchises/warehouses
    - Franchise: sees only drivers belonging to their franchise
    - Warehouse : sees only drivers belonging to their warehouse
    """
    from app.modules.fleet.models.driver import Driver
    from app.modules.fleet.models.driver_location import DriverLocation
    from app.models.delivery_assignment import DeliveryAssignment
    from app.models.pickup_assignment import PickupAssignment
    from app.models.trip_sheet import TripSheet
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # 1. Resolve role scope
    _fid, _wid, _admin = await _get_role_scope(db, current_user)

    # 2. Build driver query scoped by role
    query = (
        select(Driver)
        .options(selectinload(Driver.vehicle))
        .where(Driver.deleted_at.is_(None))
    )
    if not _admin:
        if _fid:
            query = query.where(Driver.franchise_id == _fid)
        elif _wid:
            query = query.where(Driver.warehouse_id == _wid)
        else:
            raise HTTPException(status_code=403, detail="Access denied.")

    if status:
        query = query.where(Driver.status == status)

    # Always filter online drivers unless caller explicitly passes online_only=false
    if online_only:
        query = query.where(Driver.online == True)

    drivers = (await db.execute(query)).scalars().all()

    if not drivers:
        return []

    driver_ids = [d.id for d in drivers]

    # 3. Fetch all DriverLocation records for those drivers in one query
    locations_result = await db.execute(
        select(DriverLocation).where(DriverLocation.driver_id.in_(driver_ids))
    )
    locations_map = {loc.driver_id: loc for loc in locations_result.scalars().all()}

    # 4. Fetch active assignments to determine current vehicle
    da_result = await db.execute(
        select(DeliveryAssignment)
        .options(selectinload(DeliveryAssignment.vehicle))
        .where(DeliveryAssignment.driver_id.in_(driver_ids), DeliveryAssignment.status.in_(["assigned", "in_progress"]))
    )
    da_map = {da.driver_id: da.vehicle for da in da_result.scalars().all() if da.vehicle}

    pa_result = await db.execute(
        select(PickupAssignment)
        .options(selectinload(PickupAssignment.vehicle))
        .where(PickupAssignment.driver_id.in_(driver_ids), PickupAssignment.status.in_(["assigned", "in_progress"]))
    )
    pa_map = {pa.driver_id: pa.vehicle for pa in pa_result.scalars().all() if pa.vehicle}

    ts_result = await db.execute(
        select(TripSheet)
        .options(selectinload(TripSheet.vehicle))
        .where(TripSheet.driver_id.in_(driver_ids), TripSheet.driver_status.in_(["accepted", "started", "in_progress"]))
    )
    ts_map = {ts.driver_id: ts.vehicle for ts in ts_result.scalars().all() if ts.vehicle}

    # 5. Build response
    response = []
    for driver in drivers:
        loc = locations_map.get(driver.id)
        
        # Determine current vehicle (Trip > Delivery > Pickup > Default profile vehicle)
        v = ts_map.get(driver.id) or da_map.get(driver.id) or pa_map.get(driver.id) or driver.vehicle
        
        response.append({
            "driver": {
                "id": driver.id,
                "first_name": driver.first_name,
                "last_name": driver.last_name,
                "phone": driver.phone,
                "status": driver.status,
                "online": driver.online,
                "franchise_id": driver.franchise_id,
                "warehouse_id": driver.warehouse_id,
            },
            "vehicle": {
                "id": v.id,
                "type": v.type,
                "plate_number": v.plate_number,
                "make": v.make,
                "model": v.model,
                "year": v.year,
                "color": v.color,
                "status": v.status,
            } if v else None,
            "location": {
                "lat": loc.latitude,
                "lng": loc.longitude,
                "speed": loc.speed,
                "heading": loc.heading,
                "accuracy": loc.accuracy,
                "last_updated": loc.updated_at,
            } if loc else None,
        })

    return response




# ─── Driver Document & Bank Detail Endpoints ──────────────────────────────────

@router.get("/fleet/drivers", response_model=DriverListResponse)
async def list_drivers_endpoint(
    page:          int            = Query(1,    ge=1),
    limit:         int            = Query(20,   ge=1, le=100),
    status_filter: Optional[str]  = Query(None, alias="status"),
    db:            AsyncSession   = Depends(get_db),
    current_user:  User           = Depends(get_current_user),
    _:             User           = Depends(require_permission("drivers:view")),
):
    """
    List drivers (paginated) with total counts and on-road counts.
    - Admin / Warehouse → all drivers globally.
    - Franchise user    → only drivers belonging to their franchise.
    """
    from app.modules.fleet.models.driver import Driver
    from sqlalchemy import select, func

    _fid, _wid, _admin = await _get_role_scope(db, current_user)

    # Base query for all drivers in scope
    query = select(Driver).where(Driver.deleted_at.is_(None))
    if not _admin:
        if _fid:
            query = query.where(Driver.franchise_id == _fid)
        elif _wid:
            query = query.where(Driver.warehouse_id == _wid)
        else:
            raise HTTPException(status_code=403, detail="Access denied.")

    # Calculate totals before applying pagination and specific filters
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_drivers = total_result.scalar() or 0

    onroad_result = await db.execute(
        select(func.count()).select_from(query.where(Driver.online == True).subquery())
    )
    on_road_drivers = onroad_result.scalar() or 0

    # Apply filters
    if status_filter:
        query = query.where(Driver.status == status_filter)

    # Calculate filtered total for pagination
    filtered_total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    filtered_total = filtered_total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * limit
    query = query.order_by(Driver.created_at.desc()).offset(offset).limit(limit)

    drivers = (await db.execute(query)).scalars().all()
    pages = (filtered_total + limit - 1) // limit if filtered_total > 0 else 0

    return DriverListResponse(
        items=drivers,
        total_drivers=total_drivers,
        on_road_drivers=on_road_drivers,
        page=page,
        limit=limit,
        pages=pages
    )
