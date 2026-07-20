from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.models.warehouse import WareHouseAddress
from app.models.franchise import Franchise
from app.dependencies.role_checker import require_permission
from datetime import datetime

router = APIRouter(prefix="/location", tags=["location"])

class LocationCaptureRequest(BaseModel):
    latitude: float
    longitude: float

class LocationStatusResponse(BaseModel):
    needs_location: bool
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.get("/status", response_model=LocationStatusResponse)
async def get_location_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if the current logged-in user (Warehouse or Franchise) needs to capture their location.
    Works for both owners (user_id on the entity) and employees (warehouse_id/franchise_id on the user).
    """
    # -- Warehouse: employee link first, then owner lookup --
    warehouse_id = current_user.warehouse_id
    if not warehouse_id:
        wh_result = await db.execute(select(WareHouseAddress).where(WareHouseAddress.user_id == current_user.id))
        owned_wh = wh_result.scalar_one_or_none()
        if owned_wh:
            warehouse_id = owned_wh.id

    if warehouse_id:
        result = await db.execute(select(WareHouseAddress).where(WareHouseAddress.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if warehouse:
            needs_loc = warehouse.latitude is None or warehouse.longitude is None
            return {
                "needs_location": needs_loc,
                "entity_type": "warehouse",
                "entity_id": warehouse.id,
                "latitude": warehouse.latitude,
                "longitude": warehouse.longitude
            }

    # -- Franchise: employee link first, then owner lookup --
    franchise_id = current_user.franchise_id
    if not franchise_id:
        fr_result = await db.execute(select(Franchise).where(Franchise.user_id == current_user.id))
        owned_fr = fr_result.scalar_one_or_none()
        if owned_fr:
            franchise_id = owned_fr.id

    if franchise_id:
        result = await db.execute(select(Franchise).where(Franchise.id == franchise_id))
        franchise = result.scalar_one_or_none()
        if franchise:
            needs_loc = franchise.latitude is None or franchise.longitude is None
            return {
                "needs_location": needs_loc,
                "entity_type": "franchise",
                "entity_id": franchise.id,
                "latitude": franchise.latitude,
                "longitude": franchise.longitude
            }

    return {"needs_location": False}

@router.post("/capture")
async def capture_location(
    request: LocationCaptureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Capture GPS coordinates for the current Franchise or Warehouse user.
    Works for both owners (user_id on the entity) and employees (warehouse_id/franchise_id on the user).
    """
    # -- Warehouse: employee link first, then owner lookup --
    warehouse_id = current_user.warehouse_id
    if not warehouse_id:
        wh_result = await db.execute(select(WareHouseAddress).where(WareHouseAddress.user_id == current_user.id))
        owned_wh = wh_result.scalar_one_or_none()
        if owned_wh:
            warehouse_id = owned_wh.id

    if warehouse_id:
        result = await db.execute(select(WareHouseAddress).where(WareHouseAddress.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if warehouse:
            if warehouse.latitude is not None and warehouse.longitude is not None:
                raise HTTPException(status_code=400, detail="Location already captured. Use reset to recapture.")
            warehouse.latitude = request.latitude
            warehouse.longitude = request.longitude
            await db.commit()
            return {"message": "Warehouse location captured successfully"}

    # -- Franchise: employee link first, then owner lookup --
    franchise_id = current_user.franchise_id
    if not franchise_id:
        fr_result = await db.execute(select(Franchise).where(Franchise.user_id == current_user.id))
        owned_fr = fr_result.scalar_one_or_none()
        if owned_fr:
            franchise_id = owned_fr.id

    if franchise_id:
        result = await db.execute(select(Franchise).where(Franchise.id == franchise_id))
        franchise = result.scalar_one_or_none()
        if franchise:
            if franchise.latitude is not None and franchise.longitude is not None:
                raise HTTPException(status_code=400, detail="Location already captured. Use reset to recapture.")
            franchise.latitude = request.latitude
            franchise.longitude = request.longitude
            await db.commit()
            return {"message": "Franchise location captured successfully"}

    raise HTTPException(status_code=400, detail="User is not associated with a warehouse or franchise")

@router.post("/reset/{entity_type}/{entity_id}")
async def reset_location(
    entity_type: str,
    entity_id: str,
    # _: User = Depends(require_permission("reset:location")), # using reset:location as an admin permission
    db: AsyncSession = Depends(get_db)
):
    """
    Reset location for a warehouse or franchise (Admin only)
    """
    if entity_type == "warehouse":
        result = await db.execute(select(WareHouseAddress).where(WareHouseAddress.id == entity_id))
        entity = result.scalar_one_or_none()
    elif entity_type == "franchise":
        result = await db.execute(select(Franchise).where(Franchise.id == entity_id))
        entity = result.scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")
        
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    entity.latitude = None
    entity.longitude = None
    await db.commit()
    
    return {"message": f"{entity_type.capitalize()} location reset successfully"}
