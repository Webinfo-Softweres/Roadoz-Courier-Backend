"""
Public routes — NO authentication required.
These endpoints are safe to call without any Bearer token.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.models.franchise import Franchise
from app.models.order import Order
from app.schemas.franchise import FranchiseMapItem, FranchiseMapResponse, FranchisePublicListResponse, FranchisePublicItem
from sqlalchemy import func
from collections import defaultdict
from app.models.rate_master import RateMaster




router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/franchise/map", response_model=FranchiseMapResponse)
async def get_franchises_for_map(
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active status. Pass true for active only, false for inactive only. Omit to get all.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all franchises with their location data for map display.

    Returns: id, name, franchise_code, latitude, longitude,
             city, state, country, pincode, address, phone, is_active.

    **No authentication required.**
    """
    query = select(Franchise)
    if is_active is not None:
        query = query.where(Franchise.is_active == is_active)

    result = await db.execute(query)
    franchises = result.scalars().all()

    items = [FranchiseMapItem.model_validate(f) for f in franchises]
    return FranchiseMapResponse(total=len(items), items=items)


@router.get("/franchise/list", response_model=FranchisePublicListResponse)
async def get_public_franchises(
    state: Optional[str] = Query(None, description="Filter franchises by state"),
    country: Optional[str] = Query(None, description="Filter franchises by country"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a list of franchises with their total order count.
    Can be filtered by state and country.
    
    **No authentication required.**
    """
    # Create a subquery to count orders per franchise
    order_counts_subq = (
        select(Order.franchise_id, func.count(Order.id).label("total_orders_count"))
        .group_by(Order.franchise_id)
        .subquery()
    )

    query = (
        select(
            Franchise,
            func.coalesce(order_counts_subq.c.total_orders_count, 0).label("total_orders_count")
        )
        .outerjoin(order_counts_subq, Franchise.id == order_counts_subq.c.franchise_id)
        .where(Franchise.is_active == True)
    )

    if state:
        query = query.where(Franchise.state == state)
    if country:
        query = query.where(Franchise.country == country)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for franchise, total_orders_count in rows:
        item_data = FranchisePublicItem.model_validate(franchise).model_dump()
        item_data["total_orders_count"] = total_orders_count
        items.append(FranchisePublicItem(**item_data))

    return FranchisePublicListResponse(total=len(items), items=items)




@router.get("/rate-master")
async def get_public_rate_master(
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RateMaster).order_by(RateMaster.service_type,RateMaster.zone,RateMaster.weight_up_to))
    rates = result.scalars().all()
    data = {"Surface": defaultdict(list),"Express": defaultdict(list)}
    for rate in rates:
        data[rate.service_type][rate.zone].append({"id": rate.id,"weight_up_to": float(rate.weight_up_to),"base_rate": float(rate.base_rate),})
    return {"Surface": dict(data["Surface"]),"Express": dict(data["Express"])}