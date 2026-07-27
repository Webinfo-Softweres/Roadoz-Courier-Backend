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
from app.schemas.franchise import FranchiseMapItem, FranchiseMapResponse

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
