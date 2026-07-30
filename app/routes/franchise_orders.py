from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import Optional

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.models.franchise import Franchise, OrderFranchiseAddress
from app.models.warehouse import OrderWarehouseAddress
from app.models.order import Order, OrderStatus, BagOrder
from app.schemas.order import OrderOut
from app.services.order_service import _get_franchise_for_user
from pydantic import BaseModel
from typing import List

class PaginatedFranchiseOrdersResponse(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    limit: int
    total_pages: int

router = APIRouter(prefix="/franchise/user/orders", tags=["Franchise Orders"])


@router.get("/pending", response_model=PaginatedFranchiseOrdersResponse)
async def get_pending_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by order number"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("user_orders:approve")),
):
    """
    Get all pending approval orders for the authenticated franchise.
    """
    franchise = await _get_franchise_for_user(db, current_user.id)
    if not franchise and current_user.franchise_id:
        franchise = (await db.execute(select(Franchise).where(Franchise.id == current_user.franchise_id))).scalar_one_or_none()
        
    if not franchise:
        raise HTTPException(status_code=403, detail="User does not belong to a franchise")
        
    query = select(Order).where(
        Order.franchise_id == franchise.id,
        Order.status == OrderStatus.PENDING_APPROVAL.value
    )
    
    if search:
        query = query.where(Order.order_number.ilike(f"%{search}%"))
        
    # Get total count
    count_query = select(Order.id).where(
        Order.franchise_id == franchise.id,
        Order.status == OrderStatus.PENDING_APPROVAL.value
    )
    if search:
        count_query = count_query.where(Order.order_number.ilike(f"%{search}%"))
        
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    # Apply pagination
    query = query.order_by(desc(Order.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # Load relationships
    query = query.options(
        selectinload(Order.items),
        selectinload(Order.packages),
        selectinload(Order.pickup_address),
        selectinload(Order.consignee),
        selectinload(Order.creator),
        selectinload(Order.franchise),
        selectinload(Order.bag_orders).selectinload(BagOrder.bag),
        selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
        selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        selectinload(Order.bulk_order)
    )
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    total_pages = (total + limit - 1) // limit
    
    # Convert to schema
    from app.services.order_service import _build_order_out
    items_out = [_build_order_out(o) for o in orders]
    
    return PaginatedFranchiseOrdersResponse(
        items=items_out,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.post("/{order_id}/approve", response_model=OrderOut)
async def approve_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("user_orders:approve")),
):
    """
    Approve a pending order.
    """
    franchise = await _get_franchise_for_user(db, current_user.id)
    if not franchise and current_user.franchise_id:
        franchise = (await db.execute(select(Franchise).where(Franchise.id == current_user.franchise_id))).scalar_one_or_none()
        
    if not franchise:
        raise HTTPException(status_code=403, detail="User does not belong to a franchise")
        
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.items),
        selectinload(Order.packages),
        selectinload(Order.pickup_address),
        selectinload(Order.consignee),
        selectinload(Order.creator),
        selectinload(Order.franchise),
        selectinload(Order.bag_orders).selectinload(BagOrder.bag),
        selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
        selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        selectinload(Order.bulk_order)
    )
    order = (await db.execute(query)).scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.franchise_id != franchise.id:
        raise HTTPException(status_code=403, detail="Order does not belong to your franchise")
        
    if order.status != OrderStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Order is not in PENDING_APPROVAL status")
        
    order.previous_status = order.status
    order.status = OrderStatus.PROCESSING.value
    
    await db.flush()
    await db.commit()
    
    from app.services.order_service import _build_order_out
    return _build_order_out(order)


@router.post("/{order_id}/reject", response_model=OrderOut)
async def reject_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("user_orders:reject")),
):
    """
    Reject a pending order.
    """
    franchise = await _get_franchise_for_user(db, current_user.id)
    if not franchise and current_user.franchise_id:
        franchise = (await db.execute(select(Franchise).where(Franchise.id == current_user.franchise_id))).scalar_one_or_none()
        
    if not franchise:
        raise HTTPException(status_code=403, detail="User does not belong to a franchise")
        
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.items),
        selectinload(Order.packages),
        selectinload(Order.pickup_address),
        selectinload(Order.consignee),
        selectinload(Order.creator),
        selectinload(Order.franchise),
        selectinload(Order.bag_orders).selectinload(BagOrder.bag),
        selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
        selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        selectinload(Order.bulk_order)
    )
    order = (await db.execute(query)).scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.franchise_id != franchise.id:
        raise HTTPException(status_code=403, detail="Order does not belong to your franchise")
        
    if order.status != OrderStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Order is not in PENDING_APPROVAL status")
        
    order.previous_status = order.status
    order.status = OrderStatus.REJECTED.value
    
    await db.flush()
    await db.commit()
    
    from app.services.order_service import _build_order_out
    return _build_order_out(order)


@router.get("/{order_id}", response_model=OrderOut)
async def get_franchise_order_details(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("user_orders:approve")),
):
    """
    Get details of an order for a franchise.
    """
    franchise = await _get_franchise_for_user(db, current_user.id)
    if not franchise and current_user.franchise_id:
        franchise = (await db.execute(select(Franchise).where(Franchise.id == current_user.franchise_id))).scalar_one_or_none()
        
    if not franchise:
        raise HTTPException(status_code=403, detail="User does not belong to a franchise")
        
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.items),
        selectinload(Order.packages),
        selectinload(Order.pickup_address),
        selectinload(Order.consignee),
        selectinload(Order.creator),
        selectinload(Order.franchise),
        selectinload(Order.bag_orders).selectinload(BagOrder.bag),
        selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
        selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        selectinload(Order.bulk_order)
    )
    order = (await db.execute(query)).scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.franchise_id != franchise.id:
        raise HTTPException(status_code=403, detail="Order does not belong to your franchise")
        
    from app.services.order_service import _build_order_out
    return _build_order_out(order)
