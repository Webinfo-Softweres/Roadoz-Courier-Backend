from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.models.order import BulkOrder, Order
from app.services.order_service import _resolve_franchise_id, _resolve_warehouse_id

router = APIRouter(prefix="/bulk-orders", tags=["Bulk Orders"])

@router.delete("/delete/{bulk_order_id}/")
async def delete_bulk_order(
    bulk_order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("bulk_orders:delete"))
):
    franchise_id = await _resolve_franchise_id(db, current_user)
    is_global = not franchise_id and not await _resolve_warehouse_id(db, current_user)

    result = await db.execute(select(BulkOrder).where(BulkOrder.id == bulk_order_id))
    bulk_order = result.scalar_one_or_none()

    if not bulk_order:
        return JSONResponse(status_code=404, content={"detail": "Bulk order not found"})

    if not is_global:
        if bulk_order.franchise_id != franchise_id:
            return JSONResponse(status_code=403, content={"detail": "Not allowed to delete resource outside your franchise scope"})

    order_exists = await db.execute(select(Order.id).where(Order.bulk_order_id == bulk_order_id).limit(1))
    if order_exists.scalar_one_or_none():
        return JSONResponse(status_code=400, content={"detail": "BulkOrder cannot be deleted because orders are linked to it"})

    await db.delete(bulk_order)
    await db.commit()

    return {"detail": "Bulk order deleted successfully"}
