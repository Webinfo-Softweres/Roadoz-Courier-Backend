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
from app.services.order_service import _get_franchise_for_user, _resolve_franchise_id, _resolve_warehouse_id
from pydantic import BaseModel
from typing import List
from datetime import date

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


# @router.post("/{order_id}/approve", response_model=OrderOut)
# async def approve_order(
#     order_id: str,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     _: User = Depends(require_permission("user_orders:approve")),
# ):
#     """
#     Approve a pending order.
#     """
#     franchise = await _get_franchise_for_user(db, current_user.id)
#     if not franchise and current_user.franchise_id:
#         franchise = (await db.execute(select(Franchise).where(Franchise.id == current_user.franchise_id))).scalar_one_or_none()
        
#     if not franchise:
#         raise HTTPException(status_code=403, detail="User does not belong to a franchise")
        
#     query = select(Order).where(Order.id == order_id).options(
#         selectinload(Order.items),
#         selectinload(Order.packages),
#         selectinload(Order.pickup_address),
#         selectinload(Order.consignee),
#         selectinload(Order.creator),
#         selectinload(Order.franchise),
#         selectinload(Order.bag_orders).selectinload(BagOrder.bag),
#         selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
#         selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
#         selectinload(Order.bulk_order)
#     )
#     order = (await db.execute(query)).scalar_one_or_none()
    
#     if not order:
#         raise HTTPException(status_code=404, detail="Order not found")
        
#     if order.franchise_id != franchise.id:
#         raise HTTPException(status_code=403, detail="Order does not belong to your franchise")
        
#     if order.status != OrderStatus.PENDING_APPROVAL.value:
#         raise HTTPException(status_code=400, detail="Order is not in PENDING_APPROVAL status")
        
#     order.previous_status = order.status
#     order.status = OrderStatus.PROCESSING.value
    
#     await db.flush()
#     await db.commit()
    
#     from app.services.order_service import _build_order_out
#     return _build_order_out(order)


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


# @router.get("/approvedordre", response_model=PaginatedFranchiseOrdersResponse)
# async def get_approved_orders(
#     page: int = Query(1, ge=1, description="Page number"),
#     limit: int = Query(10, ge=1, le=100, description="Items per page"),
#     search: Optional[str] = Query(None, description="Search by order number or consignee name"),
#     start_date: Optional[date] = Query(None, description="Filter by approved date (from)"),
#     end_date: Optional[date] = Query(None, description="Filter by approved date (to)"),
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     _: User = Depends(require_permission("user_orders:approve")),
# ):
#     """
#     Get all approved orders (status = Processing).

#     - **Franchise user**: sees only orders belonging to their franchise.
#     - **Warehouse user**: sees only orders linked to their warehouse.
#     - **Super Admin**: sees all approved orders across the system.
#     """
#     from sqlalchemy import func, and_
#     from datetime import datetime, time as dt_time

#     franchise_id = await _resolve_franchise_id(db, current_user)
#     warehouse_id = await _resolve_warehouse_id(db, current_user)
#     is_super_admin = (franchise_id is None and warehouse_id is None)

#     # Base filter: status must be Processing (approved)
#     base_filter = [Order.status == OrderStatus.PROCESSING.value]

#     if not is_super_admin:
#         if franchise_id:
#             base_filter.append(Order.franchise_id == franchise_id)
#         elif warehouse_id:
#             base_filter.append(Order.warehouse_id == warehouse_id)

#     if search:
#         from sqlalchemy import or_
#         from app.models.consignee import Consignee
#         base_filter.append(
#             or_(
#                 Order.order_number.ilike(f"%{search}%"),
#             )
#         )

#     if start_date:
#         base_filter.append(Order.updated_at >= datetime.combine(start_date, dt_time.min))
#     if end_date:
#         base_filter.append(Order.updated_at <= datetime.combine(end_date, dt_time.max))

#     # Count total
#     count_q = select(func.count(Order.id)).where(and_(*base_filter))
#     total = (await db.execute(count_q)).scalar_one()

#     # Fetch paginated
#     query = (
#         select(Order)
#         .where(and_(*base_filter))
#         .order_by(desc(Order.updated_at))
#         .offset((page - 1) * limit)
#         .limit(limit)
#         .options(
#             selectinload(Order.items),
#             selectinload(Order.packages),
#             selectinload(Order.pickup_address),
#             selectinload(Order.consignee),
#             selectinload(Order.creator),
#             selectinload(Order.franchise),
#             selectinload(Order.bag_orders).selectinload(BagOrder.bag),
#             selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
#             selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
#             selectinload(Order.bulk_order),
#         )
#     )

#     orders = (await db.execute(query)).scalars().all()
#     total_pages = (total + limit - 1) // limit if total > 0 else 0

#     from app.services.order_service import _build_order_out
#     return PaginatedFranchiseOrdersResponse(
#         items=[_build_order_out(o) for o in orders],
#         total=total,
#         page=page,
#         limit=limit,
#         total_pages=total_pages,
#     )


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
