from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.schemas.order import (
    PickupAddressCreate,
    PickupAddressOut,
    PickupAddressListResponse,
    ConsigneeCreate,
    ConsigneeOut,
    ConsigneeListResponse,
    OrderCreate,
    OrderOut,
    OrderListResponse,
)
from app.services.order_service import (
    search_pickup_addresses,
    create_pickup_address,
    search_consignees,
    create_consignee,
    create_order,
    list_orders,
    get_order,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── Pickup Addresses ───────────────────────────────────────────────────────


@router.get("/pickup-addresses", response_model=PickupAddressListResponse)
async def search_pickup_addresses_endpoint(
    search: Optional[str] = Query(None, description="Search by nickname, contact name, address, city, or pincode"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("pickup_addresses:view")),
):
    return await search_pickup_addresses(db, current_user, search=search)


@router.post("/pickup-addresses", response_model=PickupAddressOut, status_code=201)
async def create_pickup_address_endpoint(
    data: PickupAddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("pickup_addresses:create")),
):
    return await create_pickup_address(db, data, current_user)


# ── Consignees ─────────────────────────────────────────────────────────────


@router.get("/consignees", response_model=ConsigneeListResponse)
async def search_consignees_endpoint(
    search: Optional[str] = Query(None, description="Search by name, email, or mobile"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("consignees:view")),
):
    return await search_consignees(db, current_user, search=search)


@router.post("/consignees", response_model=ConsigneeOut, status_code=201)
async def create_consignee_endpoint(
    data: ConsigneeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("consignees:create")),
):
    return await create_consignee(db, data, current_user)


# ── Orders ─────────────────────────────────────────────────────────────────


@router.post("", response_model=OrderOut, status_code=201)
async def create_order_endpoint(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("orders:create")),
):
    return await create_order(db, data, current_user)


@router.get("", response_model=OrderListResponse)
async def list_orders_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by order number"),
    status: Optional[str] = Query(None, description="Filter by status"),
    order_type: Optional[str] = Query(None, description="Filter by order type (B2C, B2B, International)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("orders:view")),
):
    return await list_orders(
        db, current_user, page=page, limit=limit,
        search=search, status_filter=status, order_type=order_type,
    )


@router.get("/{order_id}", response_model=OrderOut)
async def get_order_endpoint(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("orders:view")),
):
    return await get_order(db, order_id, current_user)
