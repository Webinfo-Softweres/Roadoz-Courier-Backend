import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.models.parcel_tripsheet import ParcelTripSheet, ParcelTripSheetOrder
from app.models.parcel_order import ParcelOrder
from app.schemas.parcel_tripsheet import (
    ParcelTripSheetCreate,
    ParcelTripSheetUpdate,
    ParcelTripSheetOut,
    ParcelTripSheetDetail,
    ParcelTripSheetListResponse,
)
from app.schemas.parcel_order import ParcelOrderOut

router = APIRouter(prefix="/parcel-tripsheets", tags=["Parcel Trip Sheets"])


# ── helpers ──────────────────────────────────────────────────────────────────

async def _resolve_franchise_id(db: AsyncSession, user: User) -> Optional[str]:
    from app.services.order_service import _resolve_franchise_id as _rfi
    return await _rfi(db, user)


async def _resolve_warehouse_id(db: AsyncSession, user: User) -> Optional[str]:
    from app.services.order_service import _resolve_warehouse_id as _rwi
    return await _rwi(db, user)


def _scope_filters(franchise_id, warehouse_id) -> list:
    """Build ownership filters based on caller scope."""
    if franchise_id:
        return [ParcelTripSheet.franchise_id == franchise_id]
    if warehouse_id:
        return [ParcelTripSheet.warehouse_id == warehouse_id]
    return []  # admin – no filter, see all


async def _get_trip_or_404(
    id: str,
    db: AsyncSession,
    franchise_id: Optional[str],
    warehouse_id: Optional[str],
) -> ParcelTripSheet:
    filters = _scope_filters(franchise_id, warehouse_id)
    query = select(ParcelTripSheet).where(ParcelTripSheet.id == id)
    if filters:
        query = query.where(and_(*filters))
    trip = (await db.execute(query)).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Parcel Trip Sheet not found")
    return trip


def _build_detail_response(trip: ParcelTripSheet, orders: list) -> dict:
    """Build a ParcelTripSheetDetail dict manually to avoid Pydantic ORM validation issues."""
    base = ParcelTripSheetOut.model_validate(trip).model_dump()
    base["parcel_orders"] = [ParcelOrderOut.model_validate(o).model_dump() for o in orders]
    return base


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/create", response_model=ParcelTripSheetOut, status_code=201)
async def create_parcel_tripsheet(
    data: ParcelTripSheetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ = Depends(require_permission("parcelorder:create")),
):
    if not data.barcodes:
        raise HTTPException(status_code=400, detail="Trip sheet must include at least one parcel barcode.")

    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    # Fetch orders by order_number or barcode string
    orders_res = await db.execute(
        select(ParcelOrder).where(
            or_(
                ParcelOrder.barcode.in_(data.barcodes),
                ParcelOrder.order_number.in_(data.barcodes)
            )
        )
    )
    orders = orders_res.scalars().all()
    if not orders:
        raise HTTPException(status_code=400, detail="No matching parcel orders found for the given barcodes.")

    new_trip = ParcelTripSheet(
        driver_name=data.driver_name,
        mobile=data.mobile,
        email=data.email,
        gender=data.gender,
        city=data.city,
        state=data.state,
        country=data.country,
        address=data.address,
        vehicle_number=data.vehicle_number,
        vehicle_type=data.vehicle_type,
        vehicle_model=data.vehicle_model,
        fuel_type=data.fuel_type,
        city_routes=data.city_routes,
        city_destination=data.city_destination,
        starting_kilometer=data.starting_kilometer,
        ending_kilometer=data.ending_kilometer,
        created_by=current_user.id,
        franchise_id=franchise_id,
        warehouse_id=warehouse_id,
    )
    db.add(new_trip)
    await db.flush()  # get new_trip.id before linking

    for order in orders:
        order.status = "In Transit"
        db.add(ParcelTripSheetOrder(
            trip_sheet_id=new_trip.id,
            parcel_order_id=order.id,
        ))

    await db.commit()
    await db.refresh(new_trip)
    return new_trip


# ── LIST ──────────────────────────────────────────────────────────────────────
@router.get("/list", response_model=ParcelTripSheetListResponse)
async def list_parcel_tripsheets(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_permission("parcelorder:view")),
):
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    filters = _scope_filters(franchise_id, warehouse_id)

    query = select(ParcelTripSheet)

    if filters:
        query = query.where(and_(*filters))

    if search:
        query = query.where(
            or_(
                ParcelTripSheet.driver_name.ilike(f"%{search}%"),
                ParcelTripSheet.vehicle_number.ilike(f"%{search}%"),
            )
        )

    total = (
        await db.execute(
            select(func.count()).select_from(query.subquery())
        )
    ).scalar_one()

    offset = (page - 1) * limit

    result = await db.execute(
        query.order_by(ParcelTripSheet.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    items = result.scalars().all()

    # Convert old string values to list
    for item in items:
        if isinstance(item.city_routes, str):
            item.city_routes = [
                route.strip()
                for route in item.city_routes.split("→")
                if route.strip()
            ]

    return ParcelTripSheetListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 1,
    )
# ── DETAIL ────────────────────────────────────────────────────────────────────

@router.get("/onebyone/{id}", response_model=ParcelTripSheetDetail)
async def get_parcel_tripsheet_details(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ = Depends(require_permission("parcelorder:view")),
):
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    trip = await _get_trip_or_404(id, db, franchise_id, warehouse_id)

    # Fetch linked orders through the relational join table
    orders_res = await db.execute(
        select(ParcelOrder)
        .join(ParcelTripSheetOrder, ParcelOrder.id == ParcelTripSheetOrder.parcel_order_id)
        .where(ParcelTripSheetOrder.trip_sheet_id == id)
        .options(selectinload(ParcelOrder.creator), selectinload(ParcelOrder.franchise))
    )
    orders = orders_res.scalars().all()

    return _build_detail_response(trip, orders)


# ── UPDATE ────────────────────────────────────────────────────────────────────

@router.put("/update/{id}", response_model=ParcelTripSheetDetail)
async def update_parcel_tripsheet(
    id: str,
    data: ParcelTripSheetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ = Depends(require_permission("parcelorder:edit")),
):
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    trip = await _get_trip_or_404(id, db, franchise_id, warehouse_id)

    # Apply only provided fields
    update_data = data.model_dump(exclude_unset=True)
    new_barcodes = update_data.pop("barcodes", None)

    for field, value in update_data.items():
        setattr(trip, field, value)

    # If barcodes list was updated, rebuild the linked orders
    if new_barcodes is not None:
        # Delete old links
        await db.execute(
            ParcelTripSheetOrder.__table__.delete().where(
                ParcelTripSheetOrder.trip_sheet_id == id
            )
        )
        # Fetch & link new orders
        orders_res = await db.execute(
            select(ParcelOrder).where(
                or_(
                    ParcelOrder.barcode.in_(new_barcodes),
                    ParcelOrder.order_number.in_(new_barcodes),
                )
            )
        )
        new_orders = orders_res.scalars().all()
        for order in new_orders:
            order.status = "In Transit"
            db.add(ParcelTripSheetOrder(
                trip_sheet_id=trip.id,
                parcel_order_id=order.id,
            ))

    await db.commit()
    await db.refresh(trip)

    # Refetch linked orders for response
    orders_res2 = await db.execute(
        select(ParcelOrder)
        .join(ParcelTripSheetOrder, ParcelOrder.id == ParcelTripSheetOrder.parcel_order_id)
        .where(ParcelTripSheetOrder.trip_sheet_id == id)
        .options(selectinload(ParcelOrder.creator), selectinload(ParcelOrder.franchise))
    )
    orders = orders_res2.scalars().all()

    return _build_detail_response(trip, orders)


# ── DELETE ────────────────────────────────────────────────────────────────────

@router.delete("/delete/{id}", status_code=204)
async def delete_parcel_tripsheet(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ = Depends(require_permission("parcelorder:delete")),
):
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    trip = await _get_trip_or_404(id, db, franchise_id, warehouse_id)

    await db.delete(trip)
    await db.commit()
