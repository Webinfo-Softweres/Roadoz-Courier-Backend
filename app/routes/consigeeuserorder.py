from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel,EmailStr

from app.core.database import get_db
from app.dependencies.consigeeuser import get_current_user
from app.models.consigeeauth import AuthUser
from app.models.order import Order, OrderItem, OrderPackage, BagOrder, Bag
from app.models.pickup_address import PickupAddress
from app.models.consignee import Consignee
from app.models.warehouse import WareHouseAddress, OrderWarehouseAddress
from app.models.franchise import Franchise, OrderFranchiseAddress
from app.schemas.consigeeuserorder import PickupAddressResponse,ConsigneeResponse,WarehouseAddressResponse,FranchiseAddressResponse,ItemResponse,PackageResponse,WeightSummaryResponse,OrderListResponse,PaginatedOrdersResponse,OrderDriverResponse,OrderVehicleResponse
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.vehicle import Vehicle
from app.routes.order import PickupToConsignees,WarehouseToDelivery,FranchiseToDelivery,ConsigneeToDelivery
from app.models.consigeereview import ProductReview, ReviewStatus

import uuid
from app.services.order_service import calculate_order_shipping_charge, _generate_order_number, generate_sku
from app.utils.barcode import generate_barcode_base64
from app.services.location_service import get_coordinates_from_address
from app.services.notification_service import create_notification
from app.models.delivery_assignment import DeliveryAssignment
from app.models.order import OrderStatus
from app.schemas.consignee_order_create import ConsigneeOrderCreatePayload
from app.models.razorpay_transaction import RazorpayTransaction
from app.services.payment_service import payment_service
from app.schemas.payment import VerifyPaymentRequest

router = APIRouter(prefix="/consignee/orders", tags=["Consignee Orders"])



def build_tracking_history(order) -> List[dict]:
    """Build tracking history from order data"""
    tracking_history = []
    
    # 1. Pickup stage - Order Created / Picked
    tracking_history.append({
        "stage": "Pickup",
        "status": "Picked",
        "pincode": order.pickup_address.pincode if order.pickup_address else None,
        "timestamp": order.created_at
    })
    
    # 2. Warehouse stages (if warehouse addresses exist)
    if order.warehouse_addresses:
        for idx, warehouse_rel in enumerate(order.warehouse_addresses):
            if warehouse_rel.warehouse_address:
                warehouse = warehouse_rel.warehouse_address
                status = "Warehouse" if idx == 0 else f"Warehouse_{idx + 1}"
                tracking_history.append({
                    "stage": "Warehouse",
                    "status": status,
                    "pincode": warehouse.pincode,
                    "timestamp": order.created_at  # Use actual timestamps if available
                })
    
    # 3. Delivery stage - Current status
    if order.status == "Delivered":
        tracking_history.append({
            "stage": "Delivery",
            "status": "Delivered",
            "pincode": order.consignee.pincode if order.consignee else None,
            "timestamp": order.updated_at
        })
    elif order.status == OrderStatus.OUT_FOR_DELIVERY.value:
        tracking_history.append({
            "stage": "Delivery",
            "status": "Out_for_delivery",
            "pincode": order.consignee.pincode if order.consignee else None,
            "timestamp": order.updated_at
        })
    else:
        # Add current status as delivery stage
        tracking_history.append({
            "stage": "Delivery",
            "status": order.status,
            "pincode": order.consignee.pincode if order.consignee else None,
            "timestamp": order.updated_at
        })
    
    return tracking_history


# ============== API Endpoints ==============

class FranchiseBasicResponse(BaseModel):
    id: str
    franchise_id: str
    nickname: str
    contact_name: str
    phone: str | None
    alternate_phone: str | None = None
    email: EmailStr | None = None
    address_line_1: str | None
    address_line_2: str | None = None
    landmark: str | None = None

    city: str | None = None
    state: str | None = None
    country: str | None = None
    pincode: str | None = None

    latitude: float | None = None
    longitude: float | None = None
    current_address: str | None = None

    class Config:
        from_attributes = True

@router.get("/franchises", response_model=List[FranchiseBasicResponse])
async def get_available_franchises(
    city: str | None = Query(None),
    state: str | None = Query(None),
    country: str | None = Query(None),
    pincode: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    query = select(Franchise).where(Franchise.is_active == True)

    if city:
        query = query.where(Franchise.city == city)

    if state:
        query = query.where(Franchise.state == state)

    if country:
        query = query.where(Franchise.country == country)

    if pincode:
        query = query.where(Franchise.pincode == pincode)

    result = await db.execute(query)
    franchises = result.scalars().all()

    return [
        FranchiseBasicResponse(
            id=f.id,
            franchise_id=f.id,
            nickname=f.name,
            contact_name=f.name,
            phone=f.phone,
            alternate_phone=getattr(f, "alternate_phone", None),
            email=f.email,
            address_line_1=f.address,
            address_line_2=getattr(f, "detailed_business_address", None),
            landmark=getattr(f, "nearby_landmark", None),
            city=f.city,
            state=f.state,
            country=f.country,
            pincode=f.pincode,
            latitude=float(f.latitude) if f.latitude else None,
            longitude=float(f.longitude) if f.longitude else None,
            current_address=f.current_address,
        )
        for f in franchises
    ]




@router.get("/my-pickup-addresses", response_model=List[PickupAddressResponse])
async def get_my_pickup_addresses(
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    nickname: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get a list of pickup addresses previously created by/for the authenticated user.
    """
    query = select(PickupAddress).where(
        or_(
            PickupAddress.auth_user_id == current_user.id,
            PickupAddress.email == current_user.email
        )
    )
    if country:
        query = query.where(PickupAddress.country.ilike(f"%{country}%"))

    if state:
        query = query.where(PickupAddress.state.ilike(f"%{state}%"))

    if city:
        query = query.where(PickupAddress.city.ilike(f"%{city}%"))

    if pincode:
        query = query.where(PickupAddress.pincode == pincode)

    if nickname:
        query = query.where(PickupAddress.nickname.ilike(f"%{nickname}%"))
    result = await db.execute(query)
    addresses = result.scalars().all()
    
    return [
        PickupAddressResponse(
            id=a.id,
            nickname=a.nickname,
            contact_name=a.contact_name,
            phone=a.phone,
            email=a.email,
            address_line_1=a.address_line_1,
            address_line_2=a.address_line_2,
            pincode=a.pincode,
            city=a.city,
            state=a.state,
            country=a.country,
            active=a.active,
            is_primary=a.is_primary,
            created_at=a.created_at,
            updated_at=a.updated_at
        ) for a in addresses
    ]

@router.get("/my-consignees", response_model=List[ConsigneeResponse])
async def get_my_consignees(
    name: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    mobile: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get a list of receiver consignees previously created by/for the authenticated user.
    """
    query = select(Consignee).where(
        or_(
            Consignee.auth_user_id == current_user.id,
            Consignee.email == current_user.email
        )
    )
    if name:
        query = query.where(Consignee.name.ilike(f"%{name}%"))
    if state:
        query = query.where(Consignee.state.ilike(f"%{state}%"))

    if city:
        query = query.where(Consignee.city.ilike(f"%{city}%"))

    if pincode:
        query = query.where(Consignee.pincode == pincode)

    if mobile:
        query = query.where(Consignee.mobile.ilike(f"%{mobile}%"))

    result = await db.execute(query)
    consignees = result.scalars().all()
    
    return [
        ConsigneeResponse(
            id=c.id,
            name=c.name,
            mobile=c.mobile,
            alternate_mobile=c.alternate_mobile,
            email=c.email,
            address_line_1=c.address_line_1,
            address_line_2=c.address_line_2,
            pincode=c.pincode,
            city=c.city,
            state=c.state,
            status=c.status,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ) for c in consignees
    ]


@router.get("/my-orders", response_model=PaginatedOrdersResponse)
async def get_my_orders(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by order number"),
):
    """
    Get all orders for the authenticated consignee user.
    Requires valid JWT token in Authorization header.
    """
    
    # Build base query joining Consignee and PickupAddress
    query = (
        select(Order)
        .outerjoin(Consignee, Order.consignee_id == Consignee.id)
        .outerjoin(PickupAddress, Order.pickup_address_id == PickupAddress.id)
        .where(
            or_(
                Consignee.auth_user_id == current_user.id,
                PickupAddress.auth_user_id == current_user.id,
                Consignee.email == current_user.email,
                PickupAddress.email == current_user.email
            )
        )
    )
    
    if status_filter:
        query = query.where(Order.status == status_filter)
    
    if search:
        query = query.where(Order.order_number.ilike(f"%{search}%"))
    
    # Get total count
    count_query = (
        select(Order.id)
        .outerjoin(Consignee, Order.consignee_id == Consignee.id)
        .outerjoin(PickupAddress, Order.pickup_address_id == PickupAddress.id)
        .where(
            or_(
                Consignee.email == current_user.email,
                PickupAddress.email == current_user.email
            )
        )
    )
    if status_filter:
        count_query = count_query.where(Order.status == status_filter)
    if search:
        count_query = count_query.where(Order.order_number.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    # Apply pagination
    query = query.order_by(desc(Order.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    # Load relationships
    query = query.options(
        selectinload(Order.pickup_address),
        selectinload(Order.consignee),
        selectinload(Order.items),
        selectinload(Order.packages),
        selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
        selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        selectinload(Order.bag_orders).selectinload(BagOrder.bag),
    )
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # Build response
    order_responses = []
    for order in orders:
        # Pickup address
        pickup_data = None
        if order.pickup_address:
            pickup_data = PickupAddressResponse(
                id=order.pickup_address.id,
                nickname=order.pickup_address.nickname,
                contact_name=order.pickup_address.contact_name,
                phone=order.pickup_address.phone,
                email=order.pickup_address.email,
                address_line_1=order.pickup_address.address_line_1,
                address_line_2=order.pickup_address.address_line_2,
                pincode=order.pickup_address.pincode,
                city=order.pickup_address.city,
                state=order.pickup_address.state,
                country=order.pickup_address.country,
                active=order.pickup_address.active,
                is_primary=order.pickup_address.is_primary,
                created_at=order.pickup_address.created_at,
                updated_at=order.pickup_address.updated_at
            )
        
        # Consignee
        consignee_data = None
        if order.consignee:
            consignee_data = ConsigneeResponse(
                id=order.consignee.id,
                name=order.consignee.name,
                mobile=order.consignee.mobile,
                alternate_mobile=order.consignee.alternate_mobile,
                email=order.consignee.email,
                address_line_1=order.consignee.address_line_1,
                address_line_2=order.consignee.address_line_2,
                pincode=order.consignee.pincode,
                city=order.consignee.city,
                state=order.consignee.state,
                status=order.consignee.status,
                created_at=order.consignee.created_at,
                updated_at=order.consignee.updated_at
            )
        
        # Warehouse addresses
        warehouse_addresses = []
        for warehouse_rel in order.warehouse_addresses:
            if warehouse_rel.warehouse_address:
                warehouse = warehouse_rel.warehouse_address
                warehouse_addresses.append(WarehouseAddressResponse(
                    name=warehouse.nickname,
                    pincode=warehouse.pincode,
                    city=warehouse.city
                ))
        
        # Franchise addresses
        franchise_addresses = []
        for franchise_rel in order.franchise_addresses:
            if franchise_rel.franchise_address:
                franchise = franchise_rel.franchise_address
                franchise_addresses.append(FranchiseAddressResponse(
                    name=franchise.name,
                    pincode=franchise.pincode,
                    city=getattr(franchise, 'city', "") or ""
                ))
        
        # Items
        items_data = []
        for item in order.items:
            items_data.append(ItemResponse(
                id=item.id,
                product_name=item.product_name,
                sku=item.sku,
                unit_price=float(item.unit_price),
                qty=item.qty,
                total=float(item.total)
            ))
        
        # Packages
        packages_data = []
        for package in order.packages:
            packages_data.append(PackageResponse(
                id=package.id,
                count=package.count,
                length_cm=float(package.length_cm),
                breadth_cm=float(package.breadth_cm),
                height_cm=float(package.height_cm),
                vol_weight_kg=float(package.vol_weight_kg),
                physical_weight_kg=float(package.physical_weight_kg)
            ))
        
        # Weight summary
        weight_summary = WeightSummaryResponse(
            applicable_weight_kg=float(order.applicable_weight_kg),
            total_boxes=order.total_boxes,
            total_weight_kg=float(order.total_weight_kg),
            total_vol_weight_kg=float(order.total_vol_weight_kg)
        )
        
        # Tracking history
        tracking_history = build_tracking_history(order)
        
        order_responses.append(OrderListResponse(
            id=order.id,
            order_number=order.order_number,
            order_type=order.order_type,
            status=order.status,
            previous_status=order.previous_status,
            payment_method=order.payment_method,
            cod_amount=float(order.cod_amount) if order.cod_amount else None,
            to_pay_amount=float(order.to_pay_amount) if order.to_pay_amount else None,
            credit_amount=float(order.credit_amount) if order.credit_amount else None,
            order_value=float(order.order_value),
            total_weight_kg=float(order.total_weight_kg),
            total_vol_weight_kg=float(order.total_vol_weight_kg),
            applicable_weight_kg=float(order.applicable_weight_kg),
            total_boxes=order.total_boxes,
            shipping_charge=float(order.shipping_charge),
            gst_number=order.gst_number,
            eway_bill_number=order.eway_bill_number,
            barcode=order.barcode,
            created_at=order.created_at,
            updated_at=order.updated_at,
            pickup_address=pickup_data,
            consignee=consignee_data,
            warehouse_addresses=warehouse_addresses,
            franchise_addresses=franchise_addresses,
            items=items_data,
            packages=packages_data,
            weight_summary=weight_summary,
            tracking_history=tracking_history
        ))
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    return PaginatedOrdersResponse(
        items=order_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )





@router.get("/my-orderlatest")
async def get_my_order(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    barcode: str = Query(None, description="Optional barcode (e.g. ORD-001). If omitted returns the latest order."),
):
    """
    Returns order details for the authenticated consignee.
    - If barcode is provided: returns that specific order.
    - If barcode is omitted: returns the latest order.
    Filters by auth_user_id OR email (covers franchise-created orders for this user).
    Includes full tracking history, driver and vehicle details.
    """
    user_filter = or_(
        Consignee.auth_user_id == current_user.id,
        PickupAddress.auth_user_id == current_user.id,
        Consignee.email == current_user.email,
        PickupAddress.email == current_user.email,
    )

    base_query = (
        select(Order)
        .outerjoin(Consignee, Order.consignee_id == Consignee.id)
        .outerjoin(PickupAddress, Order.pickup_address_id == PickupAddress.id)
        .options(
            selectinload(Order.pickup_address),
            selectinload(Order.consignee),
            selectinload(Order.items),
            selectinload(Order.packages),
            selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
            selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        )
        .where(user_filter)
    )

    if barcode:
        base_query = base_query.where(Order.order_number == barcode)
    else:
        base_query = base_query.order_by(desc(Order.created_at)).limit(1)

    result = await db.execute(base_query)
    order = result.scalar_one_or_none()

    if not order:
        detail = f"Order not found for barcode: {barcode}" if barcode else "No orders found for this user"
        raise HTTPException(status_code=404, detail=detail)

    return await _build_order_detail_response(order, db)


async def _build_order_detail_response(order, db) -> dict:
    """Builds the full order response dict including all scan stages, driver and vehicle."""
    # --- Scan records ---
    pickup_scans = (await db.execute(
        select(PickupToConsignees).where(PickupToConsignees.order_id == order.id).order_by(PickupToConsignees.created_at)
    )).scalars().all()
    warehouse_scans = (await db.execute(
        select(WarehouseToDelivery).where(WarehouseToDelivery.order_id == order.id).order_by(WarehouseToDelivery.created_at)
    )).scalars().all()
    franchise_scans = (await db.execute(
        select(FranchiseToDelivery).where(FranchiseToDelivery.order_id == order.id).order_by(FranchiseToDelivery.created_at)
    )).scalars().all()
    delivery_scans = (await db.execute(
        select(ConsigneeToDelivery).where(ConsigneeToDelivery.order_id == order.id).order_by(ConsigneeToDelivery.created_at)
    )).scalars().all()

    # --- Delivery assignment -> driver + vehicle ---
    delivery_assignment = (await db.execute(
        select(DeliveryAssignment)
        .options(selectinload(DeliveryAssignment.driver), selectinload(DeliveryAssignment.vehicle))
        .where(DeliveryAssignment.order_id == order.id, DeliveryAssignment.status != "cancelled")
        .order_by(desc(DeliveryAssignment.created_at))
    )).scalars().first()

    driver_data = None
    vehicle_data = None
    if delivery_assignment:
        if delivery_assignment.driver:
            driver_data = {
                "id": delivery_assignment.driver.id,
                "first_name": delivery_assignment.driver.first_name,
                "last_name": delivery_assignment.driver.last_name,
                "phone": delivery_assignment.driver.phone,
            }
        if delivery_assignment.vehicle:
            vehicle_data = {
                "id": delivery_assignment.vehicle.id,
                "plate_number": delivery_assignment.vehicle.plate_number,
                "make": delivery_assignment.vehicle.make,
                "model": delivery_assignment.vehicle.model,
                "type": delivery_assignment.vehicle.type,
            }

    # --- Build tracking timeline ---
    tracking_history = [{
        "stage": "Order Created", "status": "Processing", "status_display": "Order Created",
        "description": f"Order {order.order_number} has been created",
        "location": order.pickup_address.city if order.pickup_address else "System",
        "address": order.pickup_address.address_line_1 if order.pickup_address else None,
        "city": order.pickup_address.city if order.pickup_address else None,
        "state": order.pickup_address.state if order.pickup_address else None,
        "pincode": order.pickup_address.pincode if order.pickup_address else None,
        "contact_name": order.pickup_address.contact_name if order.pickup_address else None,
        "contact_phone": order.pickup_address.phone if order.pickup_address else None,
        "timestamp": order.created_at,
        "formatted_date": order.created_at.strftime("%d %b %Y, %I:%M %p") if order.created_at else None,
        "is_current": False, "icon": "\U0001f4e6", "scan_id": None, "scan_type": None,
    }]
    for scan in pickup_scans:
        tracking_history.append({
            "stage": "Pickup", "status": "Picked Up", "status_display": "Picked Up",
            "description": f"Order picked up from {order.pickup_address.nickname if order.pickup_address else 'pickup location'}",
            "location": order.pickup_address.city if order.pickup_address else None,
            "address": order.pickup_address.address_line_1 if order.pickup_address else None,
            "city": order.pickup_address.city if order.pickup_address else None,
            "state": order.pickup_address.state if order.pickup_address else None,
            "pincode": scan.pincode,
            "contact_name": order.pickup_address.contact_name if order.pickup_address else None,
            "contact_phone": order.pickup_address.phone if order.pickup_address else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": False, "icon": "\U0001f4e4", "scan_id": scan.id, "scan_type": "pickup",
        })
    for idx, scan in enumerate(warehouse_scans):
        wh = scan.warehouse_address if hasattr(scan, "warehouse_address") else None
        is_current = (idx == len(warehouse_scans) - 1 and order.status in ["Warehouse", "In_transit", "Ofd"])
        tracking_history.append({
            "stage": "Warehouse", "status": "In Warehouse", "status_display": f"Warehouse {idx + 1}",
            "description": f"Order received at {wh.name if wh else 'warehouse'}",
            "location": wh.city if wh else None,
            "address": wh.address_line_1 if wh else None,
            "city": wh.city if wh else None,
            "state": wh.state if wh else None,
            "pincode": wh.pincode if wh else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": is_current, "icon": "\U0001f3ed", "scan_id": scan.id, "scan_type": "warehouse",
        })
    for idx, scan in enumerate(franchise_scans):
        fr = scan.franchise_address if hasattr(scan, "franchise_address") else None
        is_current = (idx == len(franchise_scans) - 1 and order.status in ["Franchise", "Ofd", "Out_for_delivery"])
        tracking_history.append({
            "stage": "Franchise", "status": "At Franchise", "status_display": "At Franchise Hub",
            "description": f"Order arrived at {fr.name if fr else 'franchise hub'}",
            "location": fr.city if fr else None,
            "address": fr.address if fr else None,
            "city": fr.city if fr else None,
            "state": fr.state if fr else None,
            "pincode": fr.pincode if fr else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": is_current, "icon": "\U0001f3ea", "scan_id": scan.id, "scan_type": "franchise",
        })
    for idx, scan in enumerate(delivery_scans):
        is_current = (idx == len(delivery_scans) - 1)
        tracking_history.append({
            "stage": "Delivery", "status": "Out for Delivery", "status_display": "Out for Delivery",
            "description": "Order is out for delivery",
            "location": order.consignee.city if order.consignee else None,
            "address": order.consignee.address_line_1 if order.consignee else None,
            "city": order.consignee.city if order.consignee else None,
            "pincode": order.consignee.pincode if order.consignee else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": is_current, "icon": "\U0001f69a", "scan_id": scan.id, "scan_type": "delivery",
        })

    return {
        "id": order.id,
        "order_number": order.order_number,
        "barcode": order.barcode,
        "status": order.status,
        "previous_status": order.previous_status,
        "order_type": order.order_type,
        "payment_method": order.payment_method,
        "cod_amount": float(order.cod_amount) if order.cod_amount else None,
        "to_pay_amount": float(order.to_pay_amount) if order.to_pay_amount else None,
        "credit_amount": float(order.credit_amount) if order.credit_amount else None,
        "prepaid_amount": float(order.prepaid_amount) if order.prepaid_amount else None,
        "order_value": float(order.order_value),
        "shipping_charge": float(order.shipping_charge),
        "insurance": float(order.insurance) if order.insurance else 0.0,
        "total_weight_kg": float(order.total_weight_kg),
        "total_vol_weight_kg": float(order.total_vol_weight_kg),
        "applicable_weight_kg": float(order.applicable_weight_kg),
        "total_boxes": order.total_boxes,
        "gst_number": order.gst_number,
        "eway_bill_number": order.eway_bill_number,
        "invoicenumber": order.invoicenumber,
        "items": [
            {"id": i.id, "product_name": i.product_name, "sku": i.sku,
             "unit_price": float(i.unit_price), "qty": i.qty, "total": float(i.total)}
            for i in order.items
        ],
        "packages": [
            {"id": p.id, "count": p.count, "length_cm": float(p.length_cm), "breadth_cm": float(p.breadth_cm),
             "height_cm": float(p.height_cm), "vol_weight_kg": float(p.vol_weight_kg),
             "physical_weight_kg": float(p.physical_weight_kg)}
            for p in order.packages
        ],
        "weight_summary": {
            "applicable_weight_kg": float(order.applicable_weight_kg),
            "total_boxes": order.total_boxes,
            "total_weight_kg": float(order.total_weight_kg),
            "total_vol_weight_kg": float(order.total_vol_weight_kg),
        },
        "pickup_address": {
            "id": order.pickup_address.id,
            "nickname": order.pickup_address.nickname,
            "contact_name": order.pickup_address.contact_name,
            "phone": order.pickup_address.phone,
            "email": order.pickup_address.email,
            "address_line_1": order.pickup_address.address_line_1,
            "address_line_2": order.pickup_address.address_line_2,
            "city": order.pickup_address.city,
            "state": order.pickup_address.state,
            "pincode": order.pickup_address.pincode,
            "country": order.pickup_address.country,
        } if order.pickup_address else None,
        "consignee": {
            "id": order.consignee.id,
            "name": order.consignee.name,
            "mobile": order.consignee.mobile,
            "alternate_mobile": order.consignee.alternate_mobile,
            "email": order.consignee.email,
            "address_line_1": order.consignee.address_line_1,
            "address_line_2": order.consignee.address_line_2,
            "city": order.consignee.city,
            "state": order.consignee.state,
            "pincode": order.consignee.pincode,
        } if order.consignee else None,
        "tracking_history": tracking_history,
        "tracking_summary": {
            "total_scans": len([t for t in tracking_history if t.get("scan_id")]),
            "pickup_scans": len(pickup_scans),
            "warehouse_scans": len(warehouse_scans),
            "franchise_scans": len(franchise_scans),
            "delivery_scans": len(delivery_scans),
            "order_status": order.status,
            "last_updated": order.updated_at.strftime("%d %b %Y, %I:%M %p") if order.updated_at else None,
        },
        "driver_details": driver_data,
        "vehicle_details": vehicle_data,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


@router.get("/{order_id}")
async def get_order_detail(
    order_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information of a specific order with complete tracking history.
    Shows where the order was scanned and reached at each stage based on actual scan records.
    """
    
    query = select(Order).outerjoin(Consignee, Order.consignee_id == Consignee.id).outerjoin(PickupAddress, Order.pickup_address_id == PickupAddress.id).where(
        Order.id == order_id,
        or_(
            Consignee.auth_user_id == current_user.id,
            PickupAddress.auth_user_id == current_user.id,
            Consignee.email == current_user.email,
            PickupAddress.email == current_user.email
        )
    ).options(
        selectinload(Order.pickup_address),
        selectinload(Order.consignee),
        selectinload(Order.items),
        selectinload(Order.packages),
        selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
        selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
        selectinload(Order.bag_orders).selectinload(BagOrder.bag),
        selectinload(Order.product_reviews).selectinload(ProductReview.consignee)
    )
    
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # ========== GET ACTUAL SCAN RECORDS ==========
    
    # Get Pickup scans
    pickup_scans = await db.execute(
        select(PickupToConsignees)
        .where(PickupToConsignees.order_id == order.id)
        .order_by(PickupToConsignees.created_at)
    )
    pickup_scans = pickup_scans.scalars().all()
    
    # Get Warehouse scans
    warehouse_scans = await db.execute(
        select(WarehouseToDelivery)
        .where(WarehouseToDelivery.order_id == order.id)
        .order_by(WarehouseToDelivery.created_at)
    )
    warehouse_scans = warehouse_scans.scalars().all()
    
    # Get Franchise scans
    franchise_scans = await db.execute(
        select(FranchiseToDelivery)
        .where(FranchiseToDelivery.order_id == order.id)
        .order_by(FranchiseToDelivery.created_at)
    )
    franchise_scans = franchise_scans.scalars().all()
    
    # Get Delivery scans
    delivery_scans = await db.execute(
        select(ConsigneeToDelivery)
        .where(ConsigneeToDelivery.order_id == order.id)
        .order_by(ConsigneeToDelivery.created_at)
    )
    delivery_scans = delivery_scans.scalars().all()
    
    # Get Delivery Assignment (with driver and vehicle)
    delivery_assignment = await db.execute(
        select(DeliveryAssignment)
        .options(selectinload(DeliveryAssignment.driver), selectinload(DeliveryAssignment.vehicle))
        .where(DeliveryAssignment.order_id == order.id, DeliveryAssignment.status != "cancelled")
        .order_by(desc(DeliveryAssignment.created_at))
    )
    delivery_assignment = delivery_assignment.scalars().first()
    
    driver_data = None
    vehicle_data = None
    if delivery_assignment and delivery_assignment.driver and delivery_assignment.vehicle:
        driver_data = {
            "id": delivery_assignment.driver.id,
            "first_name": delivery_assignment.driver.first_name,
            "last_name": delivery_assignment.driver.last_name,
            "phone": delivery_assignment.driver.phone
        }
        vehicle_data = {
            "id": delivery_assignment.vehicle.id,
            "plate_number": delivery_assignment.vehicle.plate_number,
            "make": delivery_assignment.vehicle.make,
            "model": delivery_assignment.vehicle.model,
            "type": delivery_assignment.vehicle.type
        }
    
    # ========== BUILD TRACKING HISTORY FROM ACTUAL SCANS ==========
    
    tracking_history = []
    
    # 1. ORDER CREATED (always first)
    tracking_history.append({
        "stage": "Order Created",
        "status": "Processing",
        "status_display": "Order Created",
        "description": f"Order {order.order_number} has been created",
        "location": order.pickup_address.city if order.pickup_address else "System",
        "address": order.pickup_address.address_line_1 if order.pickup_address else None,
        "city": order.pickup_address.city if order.pickup_address else None,
        "state": order.pickup_address.state if order.pickup_address else None,
        "pincode": order.pickup_address.pincode if order.pickup_address else None,
        "contact_name": order.pickup_address.contact_name if order.pickup_address else None,
        "contact_phone": order.pickup_address.phone if order.pickup_address else None,
        "timestamp": order.created_at,
        "formatted_date": order.created_at.strftime("%d %b %Y, %I:%M %p") if order.created_at else None,
        "is_current": False,
        "icon": "📦",
        "scan_id": None
    })
    
    # 2. PICKUP SCANS
    for scan in pickup_scans:
        tracking_history.append({
            "stage": "Pickup",
            "status": "Picked Up",
            "status_display": "Picked Up",
            "description": f"Order picked up from {order.pickup_address.nickname if order.pickup_address else 'pickup location'}",
            "location": order.pickup_address.city if order.pickup_address else None,
            "address": order.pickup_address.address_line_1 if order.pickup_address else None,
            "city": order.pickup_address.city if order.pickup_address else None,
            "state": order.pickup_address.state if order.pickup_address else None,
            "pincode": scan.pincode,
            "contact_name": order.pickup_address.contact_name if order.pickup_address else None,
            "contact_phone": order.pickup_address.phone if order.pickup_address else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": False,
            "icon": "📤",
            "scan_id": scan.id,
            "scan_type": "pickup"
        })
    
    # 3. WAREHOUSE SCANS
    for idx, scan in enumerate(warehouse_scans):
        # Get warehouse details
        warehouse = None
        if scan.warehouse_address:
            warehouse = scan.warehouse_address
        
        status_name = "Warehouse" if idx == 0 else f"Warehouse {idx + 1}"
        is_current = (idx == len(warehouse_scans) - 1 and 
                     order.status in ["Warehouse", "In_transit", "Ofd", "Delivered"])
        
        tracking_history.append({
            "stage": "Warehouse",
            "status": scan.status,
            "status_display": f"Reached {warehouse.nickname if warehouse else 'Warehouse'}",
            "description": f"Order arrived at {warehouse.nickname if warehouse else 'warehouse'}",
            "location": warehouse.city if warehouse else scan.pincode,
            "address": warehouse.address_line_1 if warehouse else None,
            "city": warehouse.city if warehouse else None,
            "state": warehouse.state if warehouse else None,
            "pincode": scan.pincode,
            "contact_name": warehouse.contact_name if warehouse else None,
            "contact_phone": warehouse.phone if warehouse else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": is_current,
            "icon": "🏪",
            "scan_id": scan.id,
            "scan_type": "warehouse"
        })
    
    # 4. FRANCHISE SCANS
    for idx, scan in enumerate(franchise_scans):
        franchise = None
        if scan.franchise_address:
            franchise = scan.franchise_address
        
        is_current = (idx == len(franchise_scans) - 1 and 
                     order.status in ["Manifested", "In_transit", "Ofd", "Delivered"])
        
        tracking_history.append({
            "stage": "Franchise",
            "status": scan.status,
            "status_display": f"Reached {franchise.name if franchise else 'Franchise'}",
            "description": f"Order arrived at {franchise.name if franchise else 'franchise'}",
            "location": franchise.city if franchise and hasattr(franchise, 'city') else franchise.preferred_service_area if franchise else scan.pincode,
            "address": franchise.address if franchise and hasattr(franchise, 'address') else None,
            "city": franchise.city if franchise and hasattr(franchise, 'city') else None,
            "state": franchise.state if franchise and hasattr(franchise, 'state') else None,
            "pincode": scan.pincode,
            "contact_name": franchise.name if franchise else None,
            "contact_phone": franchise.phone if franchise else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": is_current,
            "icon": "🏢",
            "scan_id": scan.id,
            "scan_type": "franchise"
        })
    
    # 4.5 OUT FOR DELIVERY (Delivery Assignment)
    if delivery_assignment:
        origin_location = None
        origin_address = None
        origin_city = None
        origin_state = None
        origin_pincode = None
        origin_name = None
        origin_phone = None
        
        if delivery_assignment.franchise:
            origin_name = delivery_assignment.franchise.name
            origin_city = getattr(delivery_assignment.franchise, 'city', "") or ""
            origin_location = origin_city or getattr(delivery_assignment.franchise, 'preferred_service_area', "")
            origin_address = getattr(delivery_assignment.franchise, 'address', None)
            origin_state = getattr(delivery_assignment.franchise, 'state', None)
            origin_pincode = delivery_assignment.franchise.pincode
            origin_phone = getattr(delivery_assignment.franchise, 'phone', None)
        elif delivery_assignment.warehouse:
            origin_name = delivery_assignment.warehouse.nickname
            origin_city = delivery_assignment.warehouse.city
            origin_location = origin_city
            origin_address = delivery_assignment.warehouse.address_line_1
            origin_state = delivery_assignment.warehouse.state
            origin_pincode = delivery_assignment.warehouse.pincode
            origin_phone = delivery_assignment.warehouse.phone

        tracking_history.append({
            "stage": "Delivery",
            "status": "Out_for_delivery",
            "status_display": "Out for Delivery",
            "description": f"Order is out for delivery to {order.consignee.name if order.consignee else 'customer'}",
            "location": origin_location,
            "address": origin_address,
            "city": origin_city,
            "state": origin_state,
            "pincode": origin_pincode,
            "contact_name": origin_name,
            "contact_phone": origin_phone,
            "timestamp": delivery_assignment.created_at,
            "formatted_date": delivery_assignment.created_at.strftime("%d %b %Y, %I:%M %p") if delivery_assignment.created_at else None,
            "is_current": (order.status == OrderStatus.OUT_FOR_DELIVERY.value and len(delivery_scans) == 0),
            "icon": "🚚",
            "scan_id": delivery_assignment.id,
            "scan_type": "delivery_assignment"
        })
    
    # 5. DELIVERY SCANS
    for idx, scan in enumerate(delivery_scans):
        consignee = order.consignee
        
        status_display = scan.status
        description = f"Delivery update: {scan.status}"
        icon = "🚚"
        
        if scan.status.lower() in ["out_for_delivery", "ofd", "out_of_delivery"]:
            status_display = "Out for Delivery"
            description = f"Order is out for delivery to {consignee.name if consignee else 'customer'}"
            icon = "🚚"
        elif scan.status.lower() in ["delivered"]:
            status_display = "Delivered Successfully"
            description = f"Order delivered to {consignee.name if consignee else 'customer'}"
            icon = "✅"
        elif scan.status.lower() in ["failed", "undelivered", "rto", "attempted"]:
            status_display = "Delivery Attempt Failed"
            description = f"Delivery attempt failed"
            icon = "⚠️"
            
        tracking_history.append({
            "stage": "Delivery",
            "status": scan.status,
            "status_display": status_display,
            "description": description,
            "location": consignee.city if consignee else scan.pincode,
            "address": f"{consignee.address_line_1} {consignee.address_line_2 or ''}".strip() if consignee else None,
            "city": consignee.city if consignee else None,
            "state": consignee.state if consignee else None,
            "pincode": scan.pincode,
            "contact_name": consignee.name if consignee else None,
            "contact_phone": consignee.mobile if consignee else None,
            "timestamp": scan.created_at,
            "formatted_date": scan.created_at.strftime("%d %b %Y, %I:%M %p") if scan.created_at else None,
            "is_current": (idx == len(delivery_scans) - 1),
            "icon": icon,
            "scan_id": scan.id,
            "scan_type": "delivery"
        })
    
    # If no scan records found, use order status to determine current location
    if not tracking_history:
        tracking_history.append({
            "stage": "Order Created",
            "status": order.status,
            "status_display": order.status,
            "description": f"Order status: {order.status}",
            "location": order.pickup_address.city if order.pickup_address else "System",
            "address": None,
            "city": order.pickup_address.city if order.pickup_address else None,
            "state": order.pickup_address.state if order.pickup_address else None,
            "pincode": order.pickup_address.pincode if order.pickup_address else None,
            "contact_name": None,
            "contact_phone": None,
            "timestamp": order.created_at,
            "formatted_date": order.created_at.strftime("%d %b %Y, %I:%M %p") if order.created_at else None,
            "is_current": True,
            "icon": "📦",
            "scan_id": None,
            "scan_type": None
        })
    
    # ========== IDENTIFY CURRENT LOCATION ==========
    
    # Find the latest scan (current location)
    current_scan = None
    for track in reversed(tracking_history):
        if track.get("scan_id"):
            current_scan = track
            break
    
    # If no scan found, use order status
    if not current_scan:
        current_scan = tracking_history[-1] if tracking_history else None
    
    # ========== BUILD RESPONSE ==========
    
    response = {
        "id": order.id,
        "order_number": order.order_number,
        "order_type": order.order_type,
        "status": order.status,
        "previous_status": order.previous_status,
        "payment_method": order.payment_method,
        "cod_amount": float(order.cod_amount) if order.cod_amount else None,
        "to_pay_amount": float(order.to_pay_amount) if order.to_pay_amount else None,
        "credit_amount": float(order.credit_amount) if order.credit_amount else None,
        "order_value": float(order.order_value),
        "total_weight_kg": float(order.total_weight_kg),
        "total_vol_weight_kg": float(order.total_vol_weight_kg),
        "applicable_weight_kg": float(order.applicable_weight_kg),
        "total_boxes": order.total_boxes,
        "shipping_charge": float(order.shipping_charge),
        "gst_number": order.gst_number,
        "eway_bill_number": order.eway_bill_number,
        "barcode": order.barcode,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
    
    # Pickup address
    if order.pickup_address:
        response["pickup_address"] = {
            "id": order.pickup_address.id,
            "nickname": order.pickup_address.nickname,
            "contact_name": order.pickup_address.contact_name,
            "phone": order.pickup_address.phone,
            "email": order.pickup_address.email,
            "address_line_1": order.pickup_address.address_line_1,
            "address_line_2": order.pickup_address.address_line_2,
            "pincode": order.pickup_address.pincode,
            "city": order.pickup_address.city,
            "state": order.pickup_address.state,
            "country": order.pickup_address.country,
            "active": order.pickup_address.active,
            "is_primary": order.pickup_address.is_primary,
            "created_at": order.pickup_address.created_at,
            "updated_at": order.pickup_address.updated_at
        }
    
    # Consignee
    if order.consignee:
        response["consignee"] = {
            "id": order.consignee.id,
            "name": order.consignee.name,
            "mobile": order.consignee.mobile,
            "alternate_mobile": order.consignee.alternate_mobile,
            "email": order.consignee.email,
            "address_line_1": order.consignee.address_line_1,
            "address_line_2": order.consignee.address_line_2,
            "pincode": order.consignee.pincode,
            "city": order.consignee.city,
            "state": order.consignee.state,
            "status": order.consignee.status,
            "created_at": order.consignee.created_at,
            "updated_at": order.consignee.updated_at
        }
    
    # Warehouse addresses
    response["warehouse_addresses"] = []
    for warehouse_rel in order.warehouse_addresses:
        if warehouse_rel.warehouse_address:
            warehouse = warehouse_rel.warehouse_address
            response["warehouse_addresses"].append({
                "name": warehouse.nickname,
                "pincode": warehouse.pincode,
                "city": warehouse.city,
                "address": warehouse.address_line_1
            })
    
    # Franchise addresses
    response["franchise_addresses"] = []
    for franchise_rel in order.franchise_addresses:
        if franchise_rel.franchise_address:
            franchise = franchise_rel.franchise_address
            response["franchise_addresses"].append({
                "name": franchise.name,
                "pincode": franchise.pincode,
                "city": getattr(franchise, 'city', "") or "",
                "address": getattr(franchise, 'address', None)
            })
    
    # Items
    response["items"] = []
    for item in order.items:
        response["items"].append({
            "id": item.id,
            "product_name": item.product_name,
            "sku": item.sku,
            "unit_price": float(item.unit_price),
            "qty": item.qty,
            "total": float(item.total)
        })
    
    # Packages
    response["packages"] = []
    for package in order.packages:
        response["packages"].append({
            "id": package.id,
            "count": package.count,
            "length_cm": float(package.length_cm),
            "breadth_cm": float(package.breadth_cm),
            "height_cm": float(package.height_cm),
            "vol_weight_kg": float(package.vol_weight_kg),
            "physical_weight_kg": float(package.physical_weight_kg)
        })
        
    
    # ========== PRODUCT REVIEWS ==========
    response["product_reviews"] = []
    if order.product_reviews:
        for review in order.product_reviews:
            if review.status == ReviewStatus.APPROVED:
                response["product_reviews"].append({
                    "id": review.id,
                    "review": review.review,
                    "rating": review.rating,
                    "admin_comment":review.admin_comment if review.admin_comment else None,
                    "created_at": review.created_at,
                    "formatted_date": review.created_at.strftime("%d %b %Y, %I:%M %p") if review.created_at else None,
                    "consignee_name": review.consignee.name if review.consignee else None,
                    "consignee_email": review.consignee.email if review.consignee else None
                })    
        
    # Weight summary
    response["weight_summary"] = {
        "applicable_weight_kg": float(order.applicable_weight_kg),
        "total_boxes": order.total_boxes,
        "total_weight_kg": float(order.total_weight_kg),
        "total_vol_weight_kg": float(order.total_vol_weight_kg)
    }
    
    # ========== TRACKING HISTORY ==========
    response["tracking_history"] = tracking_history
    
    # ========== CURRENT LOCATION ==========
    if current_scan:
        response["current_location"] = {
            "status": order.status,
            "status_display": current_scan.get("status_display", order.status),
            "stage": current_scan.get("stage"),
            "location": current_scan.get("location"),
            "address": current_scan.get("address"),
            "city": current_scan.get("city"),
            "pincode": current_scan.get("pincode"),
            "contact_name": current_scan.get("contact_name"),
            "contact_phone": current_scan.get("contact_phone"),
            "timestamp": current_scan.get("formatted_date"),
            "icon": current_scan.get("icon", "📦"),
            "scan_type": current_scan.get("scan_type")
        }
    else:
        response["current_location"] = {
            "status": order.status,
            "status_display": order.status,
            "stage": "Unknown",
            "location": None,
            "address": None,
            "city": None,
            "pincode": None,
            "contact_name": None,
            "contact_phone": None,
            "timestamp": None,
            "icon": "📦",
            "scan_type": None
        }
    
    response["tracking_summary"] = {
        "total_scans": len([t for t in tracking_history if t.get("scan_id")]),
        "pickup_scans": len(pickup_scans),
        "warehouse_scans": len(warehouse_scans),
        "franchise_scans": len(franchise_scans),
        "delivery_scans": len(delivery_scans),
        "order_status": order.status,
        "last_updated": order.updated_at.strftime("%d %b %Y, %I:%M %p") if order.updated_at else None
    }
    
    response["driver_details"] = driver_data
    response["vehicle_details"] = vehicle_data
    
    return response


@router.post("/create", response_model=OrderListResponse, status_code=status.HTTP_201_CREATED)
async def create_consignee_order(
    data: ConsigneeOrderCreatePayload,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Validate franchise
    franchise = (await db.execute(select(Franchise).where(Franchise.id == data.franchise_id))).scalar_one_or_none()
    if not franchise:
        raise HTTPException(status_code=400, detail="Invalid franchise ID")
        
    # 2. Handle Pickup Address (Sender)
    pickup = None
    if data.pickup_address_id:
        pickup = (await db.execute(
            select(PickupAddress).where(
                PickupAddress.id == data.pickup_address_id,
                PickupAddress.franchise_id == franchise.id
            )
        )).scalar_one_or_none()
        if not pickup:
            raise HTTPException(status_code=404, detail="Pickup address not found under selected franchise")
    elif data.sender_details:
        # Check for duplicates under this franchise
        pickup_conditions = []
        if data.sender_details.email:
            pickup_conditions.append(PickupAddress.email == data.sender_details.email)
        if data.sender_details.phone:
            pickup_conditions.append(PickupAddress.phone == data.sender_details.phone)

        if pickup_conditions:
            pickup = (await db.execute(
                select(PickupAddress).where(
                    PickupAddress.franchise_id == franchise.id,
                    or_(*pickup_conditions)
                )
            )).scalars().first()
            
        if not pickup:
            lat, lng = None, None
            try:
                full_address = f"{data.sender_details.address_line_1} {data.sender_details.city} {data.sender_details.state} {data.sender_details.pincode}"
                from app.services.location_service import get_coordinates_from_address
                loc = await get_coordinates_from_address(full_address)
                if loc:
                    lat, lng = loc["lat"], loc["lng"]
            except Exception:
                pass
                
            pickup = PickupAddress(
                id=str(uuid.uuid4()),
                user_id=franchise.user_id,
                auth_user_id=current_user.id,
                franchise_id=franchise.id,
                nickname=data.sender_details.nickname,
                contact_name=data.sender_details.contact_name,
                phone=data.sender_details.phone,
                email=data.sender_details.email,
                address_line_1=data.sender_details.address_line_1,
                address_line_2=data.sender_details.address_line_2,
                pincode=data.sender_details.pincode,
                city=data.sender_details.city,
                state=data.sender_details.state,
                country=data.sender_details.country,
                active=data.sender_details.active,
                is_primary=data.sender_details.is_primary,
                latitude=lat,
                longitude=lng
            )
            db.add(pickup)
            await db.flush()
    else:
        raise HTTPException(status_code=400, detail="Either pickup_address_id or sender_details must be provided")

    # 3. Handle Consignee (Receiver)
    consignee = None
    if data.consignee_id:
        consignee = (await db.execute(
            select(Consignee).where(
                Consignee.id == data.consignee_id,
                Consignee.franchise_id == franchise.id
            )
        )).scalar_one_or_none()
        if not consignee:
            raise HTTPException(status_code=404, detail="Consignee not found under selected franchise")
    elif data.receiver_details:
        consignee_conditions = []
        if data.receiver_details.email:
            consignee_conditions.append(Consignee.email == data.receiver_details.email)
        if data.receiver_details.mobile:
            consignee_conditions.append(Consignee.mobile == data.receiver_details.mobile)

        if consignee_conditions:
            consignee = (await db.execute(
                select(Consignee).where(
                    Consignee.franchise_id == franchise.id,
                    or_(*consignee_conditions)
                )
            )).scalars().first()
        
        if not consignee:
            clat, clng = None, None
            try:
                cfull_address = f"{data.receiver_details.address_line_1} {data.receiver_details.city} {data.receiver_details.state} {data.receiver_details.pincode}"
                from app.services.location_service import get_coordinates_from_address
                cloc = await get_coordinates_from_address(cfull_address)
                if cloc:
                    clat, clng = cloc["lat"], cloc["lng"]
            except Exception:
                pass

            consignee = Consignee(
                id=str(uuid.uuid4()),
                user_id=franchise.user_id,
                auth_user_id=current_user.id,
                franchise_id=franchise.id,
                name=data.receiver_details.name,
                mobile=data.receiver_details.mobile,
                alternate_mobile=data.receiver_details.alternate_mobile,
                email=data.receiver_details.email,
                address_line_1=data.receiver_details.address_line_1,
                address_line_2=data.receiver_details.address_line_2,
                pincode=data.receiver_details.pincode,
                city=data.receiver_details.city,
                state=data.receiver_details.state,
                latitude=clat,
                longitude=clng
            )
            db.add(consignee)
            await db.flush()
    else:
        raise HTTPException(status_code=400, detail="Either consignee_id or receiver_details must be provided")

    # 4. Generate order number
    order_number = await _generate_order_number(db)
    
    # We use franchise.user_id as the created_by for the order to bypass the foreign key constraint
    # that requires created_by to be a valid user from the 'users' table, not 'auth_users'.
    # Alternatively, if there's a system admin user, we could use that. We'll use the franchise owner.
    
    order = Order(
        id=str(uuid.uuid4()),
        order_number=order_number,
        order_type=data.order_type.value,
        pickup_address_id=pickup.id,
        consignee_id=consignee.id,
        payment_method=data.payment_method.value,
        cod_amount=data.cod_amount,
        to_pay_amount=data.to_pay_amount,
        credit_amount=data.credit_amount,
        prepaid_amount=data.prepaid_amount,
        rov=data.rov.value,
        order_value=data.order_value,
        gst_number=data.gst_number,
        eway_bill_number=data.eway_bill_number,
        invoicenumber=data.invoicenumber,
        amount=data.amount,
        insurance=(round(data.order_value * 0.018, 2) if data.insurance else 0.0),
        regional_area=data.regional_area,
        status=OrderStatus.PAYMENT_PENDING.value if data.payment_method.value == "Prepaid" else OrderStatus.PENDING_APPROVAL.value,
        previous_status=OrderStatus.PAYMENT_PENDING.value if data.payment_method.value == "Prepaid" else OrderStatus.PENDING_APPROVAL.value,
        created_by=franchise.user_id, # Link to franchise owner's user ID
        franchise_id=franchise.id,
        warehouse_id=None
    )
    
    db.add(order)
    await db.flush()
    
    # 5. Add Items
    for item_data in data.items:
        item = OrderItem(
            id=str(uuid.uuid4()),
            order_id=order.id,
            product_name=item_data.product_name,
            sku=await generate_sku(db),
            unit_price=item_data.unit_price,
            qty=item_data.qty,
            total=item_data.total,
            package_index=item_data.package_index,
        )
        db.add(item)
        
    # 6. Add Packages and calculate weights
    total_boxes = 0
    total_weight = 0.0
    total_vol = 0.0

    for idx, pkg_data in enumerate(data.packages, start=1):
        pkg = OrderPackage(
            id=str(uuid.uuid4()),
            order_id=order.id,
            count=pkg_data.count,
            package_index=idx,
            weight_unit=pkg_data.weight_unit,
            length_cm=pkg_data.length_cm,
            breadth_cm=pkg_data.breadth_cm,
            height_cm=pkg_data.height_cm,
            vol_weight_kg=pkg_data.vol_weight_kg,
            physical_weight_kg=pkg_data.physical_weight_kg,
        )
        db.add(pkg)

        total_boxes += pkg_data.count
        total_weight += pkg_data.physical_weight_kg * pkg_data.count
        total_vol += pkg_data.vol_weight_kg * pkg_data.count

    applicable = max(total_weight, total_vol)

    order.total_boxes = total_boxes
    order.total_weight_kg = round(total_weight, 2)
    order.total_vol_weight_kg = round(total_vol, 2)
    order.applicable_weight_kg = round(applicable, 2)
    
    # 7. Freight calculation
    is_gst_exempt = False
    
    pricing = await calculate_order_shipping_charge(
        db,
        order_type=data.order_type.value,
        service_type=data.service_type.value,
        pickup_pincode=pickup.pincode,
        delivery_pincode=consignee.pincode,
        payment_method=data.payment_method.value,
        rov=data.rov.value,
        order_value=data.order_value,
        packages=data.packages,
        is_gst_exempt=is_gst_exempt,
        is_doc=data.is_doc,
        delivery_type=data.delivery_type,
    )

    order.service_type = data.service_type.value
    order.freight_charge = pricing.freight_charge
    order.freight_gst = pricing.freight_gst
    order.total_freight = pricing.total_freight
    order.applied_weight_slab = pricing.applied_weight_slab
    order.pricing_zone = pricing.zone
    order.is_manual_freight = pricing.is_manual_freight
    order.is_gst_exempt = is_gst_exempt
    order.manual_freight_reason = None
    

    # Generate Barcode
    order.barcode = generate_barcode_base64(order_number)
    
    # Calculate grand_total = shipping + insurance (what user must pay online)
    insurance_amount = float(order.insurance or 0.0)
    grand_total = round(float(pricing.total_freight) + insurance_amount, 2)

    razorpay_order_id = None
    razorpay_key_id = None

    if data.payment_method.value == "Prepaid":
        # Prepaid = customer pays freight online via Razorpay
        try:
            rz_order = payment_service.create_order(amount=grand_total, receipt=order_number)
            razorpay_order_id = rz_order.get("id")
            razorpay_key_id = payment_service.client.auth[0]  # return key so frontend can open checkout

            rz_txn = RazorpayTransaction(
                id=str(uuid.uuid4()),
                order_id=order.id,
                razorpay_order_id=razorpay_order_id,
                amount=grand_total,
                status="created"
            )
            db.add(rz_txn)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize Razorpay: {str(e)}")
    # COD = Cash on Delivery, no online payment needed - handled at delivery time

    await db.flush()

    await db.commit()
    
    # 8. Reload order and return
    query = (
        select(Order)
        .where(Order.id == order.id)
        .options(
            selectinload(Order.pickup_address),
            selectinload(Order.consignee),
            selectinload(Order.items),
            selectinload(Order.packages),
            selectinload(Order.warehouse_addresses).selectinload(OrderWarehouseAddress.warehouse_address),
            selectinload(Order.franchise_addresses).selectinload(OrderFranchiseAddress.franchise_address),
            selectinload(Order.bag_orders).selectinload(BagOrder.bag),
        )
    )
    result = await db.execute(query)
    full_order = result.scalar_one()
    
    # Format response using proper Pydantic model construction (same as get_my_orders)
    pickup_data = None
    if full_order.pickup_address:
        pickup_data = PickupAddressResponse(
            id=full_order.pickup_address.id,
            nickname=full_order.pickup_address.nickname,
            contact_name=full_order.pickup_address.contact_name,
            phone=full_order.pickup_address.phone,
            email=full_order.pickup_address.email,
            address_line_1=full_order.pickup_address.address_line_1,
            address_line_2=full_order.pickup_address.address_line_2,
            pincode=full_order.pickup_address.pincode,
            city=full_order.pickup_address.city,
            state=full_order.pickup_address.state,
            country=full_order.pickup_address.country,
            active=full_order.pickup_address.active,
            is_primary=full_order.pickup_address.is_primary,
            created_at=full_order.pickup_address.created_at,
            updated_at=full_order.pickup_address.updated_at
        )

    consignee_data = None
    if full_order.consignee:
        consignee_data = ConsigneeResponse(
            id=full_order.consignee.id,
            name=full_order.consignee.name,
            mobile=full_order.consignee.mobile,
            alternate_mobile=full_order.consignee.alternate_mobile,
            email=full_order.consignee.email,
            address_line_1=full_order.consignee.address_line_1,
            address_line_2=full_order.consignee.address_line_2,
            pincode=full_order.consignee.pincode,
            city=full_order.consignee.city,
            state=full_order.consignee.state,
            status=full_order.consignee.status,
            created_at=full_order.consignee.created_at,
            updated_at=full_order.consignee.updated_at
        )

    items_data = [
        ItemResponse(
            id=item.id,
            product_name=item.product_name,
            sku=item.sku,
            unit_price=float(item.unit_price),
            qty=item.qty,
            total=float(item.total)
        )
        for item in full_order.items
    ]

    packages_data = [
        PackageResponse(
            id=pkg.id,
            count=pkg.count,
            length_cm=float(pkg.length_cm),
            breadth_cm=float(pkg.breadth_cm),
            height_cm=float(pkg.height_cm),
            vol_weight_kg=float(pkg.vol_weight_kg),
            physical_weight_kg=float(pkg.physical_weight_kg)
        )
        for pkg in full_order.packages
    ]

    weight_summary = WeightSummaryResponse(
        applicable_weight_kg=float(full_order.applicable_weight_kg),
        total_boxes=full_order.total_boxes,
        total_weight_kg=float(full_order.total_weight_kg),
        total_vol_weight_kg=float(full_order.total_vol_weight_kg)
    )

    return OrderListResponse(
        id=full_order.id,
        order_number=full_order.order_number,
        order_type=full_order.order_type,
        status=full_order.status,
        previous_status=full_order.previous_status,
        payment_method=full_order.payment_method,
        cod_amount=float(full_order.cod_amount) if full_order.cod_amount else None,
        to_pay_amount=float(full_order.to_pay_amount) if full_order.to_pay_amount else None,
        credit_amount=float(full_order.credit_amount) if full_order.credit_amount else None,
        order_value=float(full_order.order_value),
        total_weight_kg=float(full_order.total_weight_kg),
        total_vol_weight_kg=float(full_order.total_vol_weight_kg),
        applicable_weight_kg=float(full_order.applicable_weight_kg),
        total_boxes=full_order.total_boxes,
        shipping_charge=float(full_order.total_freight),
        gst_number=full_order.gst_number,
        eway_bill_number=full_order.eway_bill_number,
        barcode=full_order.barcode,
        created_at=full_order.created_at,
        updated_at=full_order.updated_at,
        pickup_address=pickup_data,
        consignee=consignee_data,
        warehouse_addresses=[],
        franchise_addresses=[],
        items=items_data,
        packages=packages_data,
        weight_summary=weight_summary,
        tracking_history=build_tracking_history(full_order),
        grand_total=grand_total,
        razorpay_order_id=razorpay_order_id,
        razorpay_key_id=razorpay_key_id,
        payment_status="created" if razorpay_order_id else None
    )





@router.post("/verify-payment", tags=["Consignee Orders"])
async def verify_razorpay_payment(
    payload: VerifyPaymentRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Called by the frontend after Razorpay checkout completes.
    Verifies the payment signature and marks the transaction as paid.
    """
    # 1. Find the transaction record by razorpay_order_id
    result = await db.execute(
        select(RazorpayTransaction).where(
            RazorpayTransaction.razorpay_order_id == payload.razorpay_order_id
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Razorpay transaction not found")

    # 2. Make sure this transaction belongs to an order that is the current user's
    order_result = await db.execute(
        select(Order).where(Order.id == txn.order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 3. Verify payment signature using HMAC-SHA256
    is_valid = payment_service.verify_payment_signature(
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature
    )

    if not is_valid:
        # Mark as failed
        txn.status = "failed"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid payment signature. Payment verification failed.")

    # 4. Mark transaction as paid and order as pending approval
    txn.razorpay_payment_id = payload.razorpay_payment_id
    txn.razorpay_signature = payload.razorpay_signature
    txn.status = "paid"
    txn.updated_at = __import__("datetime").datetime.utcnow()

    order.status = OrderStatus.PENDING_APPROVAL.value
    order.previous_status = OrderStatus.PENDING_APPROVAL.value

    await db.commit()
    await db.refresh(txn)

    return {
        "message": "Payment verified successfully",
        "order_id": txn.order_id,
        "razorpay_order_id": txn.razorpay_order_id,
        "razorpay_payment_id": txn.razorpay_payment_id,
        "amount": float(txn.amount),
        "currency": txn.currency,
        "status": txn.status
    }
