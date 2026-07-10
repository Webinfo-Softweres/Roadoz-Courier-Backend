from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.models.order import Bag, BagOrder
from app.services.order_service import _resolve_franchise_id, _resolve_warehouse_id

router = APIRouter(prefix="/bags", tags=["Bags"])

@router.delete("/delete/{bag_id}/")
async def delete_bag(
    bag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("bags:delete"))
):
    franchise_id = await _resolve_franchise_id(db, current_user)
    is_global = not franchise_id and not await _resolve_warehouse_id(db, current_user)

    result = await db.execute(select(Bag).where(Bag.id == bag_id))
    bag = result.scalar_one_or_none()

    if not bag:
        return JSONResponse(status_code=404, content={"detail": "Bag not found"})

    if not is_global:
        bag_franchise_id = getattr(bag, 'franchise_id', None)
        if bag_franchise_id:
            if bag_franchise_id != franchise_id:
                return JSONResponse(status_code=403, content={"detail": "Not allowed to delete resource outside your franchise scope"})
        elif bag.created_by != current_user.id:
            creator_res = await db.execute(select(User).where(User.id == bag.created_by))
            creator = creator_res.scalar_one_or_none()
            if not creator or getattr(creator, 'franchise_id', None) != franchise_id:
                return JSONResponse(status_code=403, content={"detail": "Not allowed to delete resource outside your franchise scope"})

    bag_order_exists = await db.execute(select(BagOrder.id).where(BagOrder.bag_id == bag_id).limit(1))
    if bag_order_exists.scalar_one_or_none():
        return JSONResponse(status_code=400, content={"detail": "Bag cannot be deleted because orders are assigned to it"})

    await db.delete(bag)
    await db.commit()

    return {"detail": "Bag deleted successfully"}
