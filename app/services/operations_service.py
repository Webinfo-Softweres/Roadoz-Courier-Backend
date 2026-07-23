import math
import uuid
from datetime import date
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import and_, func, select,delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.franchise import Franchise
from app.models.operations import CashVoucher, Expense, Manifest, ManifestOrder, PodRecord, StaffAttendance
from app.models.order import Order, OrderStatus
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.operations import (
    AttendanceCreate,
    AttendanceOut,
    CashVoucherCreate,
    CashVoucherOut,
    ExpenseCreate,
    ExpenseOut,
    ManifestCreate,
    ManifestOut,
    PodCreate,
    PodOut,
)


async def _get_caller_role_name(db: AsyncSession, user_id: str) -> str | None:
    row = await db.execute(select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id))
    role = row.scalar_one_or_none()
    return role.lower() if role else None


async def _resolve_franchise_id(db: AsyncSession, user: User) -> str | None:
    if user.franchise_id:
        return user.franchise_id
    franchise = (await db.execute(select(Franchise).where(Franchise.user_id == user.id))).scalars().first()
    return franchise.id if franchise else None

async def _resolve_warehouse_id(db: AsyncSession, user: User) -> str | None:
    from app.services.order_service import _resolve_warehouse_id as _wh
    return await _wh(db, user)


async def _scope_franchise_id(db: AsyncSession, current_user: User, franchise_id: str | None) -> str | None:
    own_franchise_id = await _resolve_franchise_id(db, current_user)
    is_global = not own_franchise_id and not await _resolve_warehouse_id(db, current_user)
    if is_global:
        return franchise_id
    if franchise_id and franchise_id != own_franchise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this franchise")
    return own_franchise_id


async def _scope_warehouse_id(db: AsyncSession, current_user: User, warehouse_id: str | None) -> str | None:
    """Return warehouse_id scoped to current user (warehouse users only see their own)."""
    own_warehouse_id = await _resolve_warehouse_id(db, current_user)
    if not own_warehouse_id:
        return warehouse_id  # super admin can specify any
    return own_warehouse_id


async def _generate_voucher_no(db: AsyncSession) -> str:
    count = (await db.execute(select(func.count()).select_from(CashVoucher))).scalar_one()
    return f"VCH-{str(count + 1).zfill(6)}"


async def _generate_manifest_no(db: AsyncSession) -> str:
    count = (await db.execute(select(func.count()).select_from(Manifest))).scalar_one()
    return f"MF-{str(count + 1).zfill(6)}"


async def create_expense(db: AsyncSession, data: ExpenseCreate, current_user: User) -> ExpenseOut:
    franchise_id = await _scope_franchise_id(db, current_user, data.franchise_id)
    warehouse_id = await _scope_warehouse_id(db, current_user, getattr(data, 'warehouse_id', None))
    expense = Expense(
        id=str(uuid.uuid4()),
        franchise_id=franchise_id,
        warehouse_id=warehouse_id,
        expense_date=data.expense_date,
        expense_head=data.expense_head,
        amount=data.amount,
        approved_by=data.approved_by,
        remarks=data.remarks,
        created_by=current_user.id,
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return ExpenseOut.model_validate(expense)


async def list_expenses(db: AsyncSession, current_user: User, page: int, limit: int, date_from: date | None, date_to: date | None, franchise_id: str | None) -> dict:
    scoped_franchise_id = await _scope_franchise_id(db, current_user, franchise_id)
    scoped_warehouse_id = await _scope_warehouse_id(db, current_user, None)
    filters = []
    if scoped_franchise_id:
        filters.append(Expense.franchise_id == scoped_franchise_id)
    elif scoped_warehouse_id:
        filters.append(Expense.warehouse_id == scoped_warehouse_id)
    if date_from:
        filters.append(Expense.expense_date >= date_from)
    if date_to:
        filters.append(Expense.expense_date <= date_to)
    query = select(Expense).where(and_(*filters)).order_by(Expense.expense_date.desc())
    total = (await db.execute(select(func.count()).select_from(Expense).where(and_(*filters)))).scalar_one()
    rows = (await db.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": [ExpenseOut.model_validate(row) for row in rows], "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if total else 0}


async def create_cash_voucher(db: AsyncSession, data: CashVoucherCreate, current_user: User) -> CashVoucherOut:
    franchise_id = await _scope_franchise_id(db, current_user, data.franchise_id)
    warehouse_id = await _scope_warehouse_id(db, current_user, getattr(data, 'warehouse_id', None))
    voucher = CashVoucher(
        id=str(uuid.uuid4()),
        voucher_no=await _generate_voucher_no(db),
        franchise_id=franchise_id,
        warehouse_id=warehouse_id,
        voucher_date=data.voucher_date,
        type=data.type,
        amount=data.amount,
        payment_mode=data.payment_mode,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(voucher)
    await db.flush()
    await db.refresh(voucher)
    return CashVoucherOut.model_validate(voucher)


async def list_cash_vouchers(db: AsyncSession, current_user: User, page: int, limit: int, date_from: date | None, date_to: date | None, franchise_id: str | None) -> dict:
    scoped_franchise_id = await _scope_franchise_id(db, current_user, franchise_id)
    scoped_warehouse_id = await _scope_warehouse_id(db, current_user, None)
    filters = []
    if scoped_franchise_id:
        filters.append(CashVoucher.franchise_id == scoped_franchise_id)
    elif scoped_warehouse_id:
        filters.append(CashVoucher.warehouse_id == scoped_warehouse_id)
    if date_from:
        filters.append(CashVoucher.voucher_date >= date_from)
    if date_to:
        filters.append(CashVoucher.voucher_date <= date_to)
    total = (await db.execute(select(func.count()).select_from(CashVoucher).where(and_(*filters)))).scalar_one()
    rows = (await db.execute(select(CashVoucher).where(and_(*filters)).order_by(CashVoucher.voucher_date.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": [CashVoucherOut.model_validate(row) for row in rows], "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if total else 0}


async def create_attendance(db: AsyncSession, data: AttendanceCreate, current_user: User) -> AttendanceOut:
    user = (await db.execute(select(User).where(User.id == data.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    franchise_id = await _scope_franchise_id(db, current_user, data.franchise_id or user.franchise_id)
    warehouse_id = await _scope_warehouse_id(db, current_user, getattr(data, 'warehouse_id', None))
    attendance = StaffAttendance(id=str(uuid.uuid4()), user_id=data.user_id, franchise_id=franchise_id, warehouse_id=warehouse_id, attendance_date=data.attendance_date, check_in=data.check_in, check_out=data.check_out, status=data.status, remarks=data.remarks)
    db.add(attendance)
    await db.flush()
    await db.refresh(attendance)
    return AttendanceOut.model_validate(attendance)


async def list_attendance(db: AsyncSession, current_user: User, page: int, limit: int, attendance_date: date | None, franchise_id: str | None) -> dict:
    scoped_franchise_id = await _scope_franchise_id(db, current_user, franchise_id)
    scoped_warehouse_id = await _scope_warehouse_id(db, current_user, None)
    filters = []
    if scoped_franchise_id:
        filters.append(StaffAttendance.franchise_id == scoped_franchise_id)
    elif scoped_warehouse_id:
        filters.append(StaffAttendance.warehouse_id == scoped_warehouse_id)
    if attendance_date:
        filters.append(StaffAttendance.attendance_date == attendance_date)
    total = (await db.execute(select(func.count()).select_from(StaffAttendance).where(and_(*filters)))).scalar_one()
    rows = (await db.execute(select(StaffAttendance).where(and_(*filters)).order_by(StaffAttendance.attendance_date.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": [AttendanceOut.model_validate(row) for row in rows], "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if total else 0}


async def create_manifest(db: AsyncSession, data: ManifestCreate, current_user: User) -> ManifestOut:
    franchise_id = await _scope_franchise_id(db, current_user, data.franchise_id)
    orders = (await db.execute(select(Order).where(Order.id.in_(data.order_ids)))).scalars().all()
    found_ids = {order.id for order in orders}
    missing = [order_id for order_id in data.order_ids if order_id not in found_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Orders not found: {missing}")
    for order in orders:
        if franchise_id and order.franchise_id != franchise_id:
            raise HTTPException(status_code=403, detail=f"Order {order.order_number} is outside this franchise")
    manifest = Manifest(id=str(uuid.uuid4()), manifest_no=await _generate_manifest_no(db), franchise_id=franchise_id, manifest_date=data.manifest_date, vehicle_no=data.vehicle_no, route=data.route, created_by=current_user.id)
    db.add(manifest)
    await db.flush()
    for order in orders:
        db.add(ManifestOrder(id=str(uuid.uuid4()), manifest_id=manifest.id, order_id=order.id))
        order.status = OrderStatus.MANIFESTED
    await db.flush()
    await db.refresh(manifest)
    return ManifestOut.model_validate(manifest)


async def list_manifests(db: AsyncSession, current_user: User, page: int, limit: int, manifest_date: date | None, franchise_id: str | None) -> dict:
    scoped_franchise_id = await _scope_franchise_id(db, current_user, franchise_id)
    filters = []
    if scoped_franchise_id:
        filters.append(Manifest.franchise_id == scoped_franchise_id)
    if manifest_date:
        filters.append(Manifest.manifest_date == manifest_date)
    total = (await db.execute(select(func.count()).select_from(Manifest).where(and_(*filters)))).scalar_one()
    rows = (await db.execute(select(Manifest).where(and_(*filters)).order_by(Manifest.manifest_date.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": [ManifestOut.model_validate(row) for row in rows], "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if total else 0}


async def create_pod(db: AsyncSession, data: PodCreate, current_user: User) -> PodOut:
    order = (await db.execute(select(Order).where(Order.id == data.order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await _scope_franchise_id(db, current_user, order.franchise_id)
    existing = (await db.execute(select(PodRecord).where(PodRecord.order_id == data.order_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="POD already exists for this order")
    pod = PodRecord(id=str(uuid.uuid4()), order_id=data.order_id, receiver_name=data.receiver_name, received_at=data.received_at, delivery_staff_id=data.delivery_staff_id, otp_verified=data.otp_verified, signature_url=data.signature_url, remarks=data.remarks)
    db.add(pod)
    order.status = OrderStatus.DELIVERED
    await db.flush()
    await db.refresh(pod)
    return PodOut.model_validate(pod)


async def get_pod_by_order(db: AsyncSession, order_id: str, current_user: User) -> PodOut:
    pod = (await db.execute(select(PodRecord).where(PodRecord.order_id == order_id))).scalar_one_or_none()
    if not pod:
        raise HTTPException(status_code=404, detail="POD not found")
    await _scope_franchise_id(db, current_user, pod.order.franchise_id)
    return PodOut.model_validate(pod)


async def generate_trip_sheet(db: AsyncSession, data: "TripSheetRequest", current_user: User):
    from app.schemas.operations import TripSheetResponse, TripSheetItem
    from app.models.trip_sheet import TripSheet, TripSheetOrder
    import uuid
    
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    # Build order query scoped to the current user's franchise/warehouse
    order_filters = [Order.order_number.in_(data.barcodes)]
    if franchise_id:
        order_filters.append(Order.franchise_id == franchise_id)
    elif warehouse_id:
        order_filters.append(Order.warehouse_id == warehouse_id)

    orders = (await db.execute(select(Order).where(and_(*order_filters)))).scalars().all()
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found for given barcodes under your franchise/warehouse")

    # Detect any barcodes that were requested but not returned (out-of-scope or not found)
    found_numbers = {o.order_number for o in orders}
    missing = [b for b in data.barcodes if b not in found_numbers]
    if missing:
        raise HTTPException(
            status_code=403,
            detail=f"The following orders are not under your franchise/warehouse or do not exist: {missing}"
        )


    items = []
    topay_freight = 0.0
    topay_packages = 0
    credit_freight = 0.0
    credit_packages = 0
    cod_freight = 0.0
    cod_packages = 0
    prepaid_freight = 0.0
    prepaid_packages = 0
    total_freight = 0.0
    total_packages = 0
    
    trip_sheet_id = str(uuid.uuid4())
    trip_sheet_orders = []
    
    for idx, order in enumerate(orders, start=1):
        freight = float(order.total_freight or 0)
        boxes = int(order.total_boxes or 0)
        if boxes == 0:
            boxes = 1
            
        payment = str(order.payment_method).lower().replace(" ", "")
        if payment == "topay":
            topay_freight += freight
            topay_packages += boxes
        elif payment == "credit":
            credit_freight += freight
            credit_packages += boxes
        elif payment == "cod":
            cod_freight += freight
            cod_packages += boxes
        elif payment == "prepaid":
            prepaid_freight += freight
            prepaid_packages += boxes
            
        total_freight += freight
        total_packages += boxes
        
        items.append(TripSheetItem(
            sl_no=idx,
            order_id=order.id,
            order_number=order.order_number,
            payment_method=order.payment_method,
            total_freight=freight,
            total_boxes=boxes
        ))
        
        trip_sheet_orders.append(
            TripSheetOrder(
                trip_sheet_id=trip_sheet_id,
                order_id=order.id,
                sl_no=idx
            )
        )
        
    trip_sheet = TripSheet(
        id=trip_sheet_id,
        franchise_id=franchise_id,
        warehouse_id=warehouse_id,
        destination_franchise_id=data.destination_franchise_id,
        route_franchise_ids=data.route_franchise_ids,
        is_local=data.is_local,
        route_city=data.route_city,
        destination_city=data.destination_city,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        topay_freight=topay_freight,
        topay_packages=topay_packages,
        credit_freight=credit_freight,
        credit_packages=credit_packages,
        cod_freight=cod_freight,
        cod_packages=cod_packages,
        prepaid_freight=prepaid_freight,
        prepaid_packages=prepaid_packages,
        total_freight=total_freight,
        total_packages=total_packages,
        created_by=current_user.id
    )
    
    db.add(trip_sheet)
    db.add_all(trip_sheet_orders)
    await db.flush()

    # Send real-time WebSocket notification to the destination franchise
    if data.destination_franchise_id:
        from app.websocket.franchise_manager import franchise_manager
        # Resolve sender franchise name for the notification payload
        sender_name = None
        sender_address = None
        sender_pincode = None
        if franchise_id:
            from app.models.franchise import Franchise as FranchiseModel
            sender = (await db.execute(select(FranchiseModel).where(FranchiseModel.id == franchise_id))).scalar_one_or_none()
            if sender:
                sender_name = sender.name
                sender_address=sender.address
                sender_pincode=sender.pincode
        await franchise_manager.send_to_franchise(
            data.destination_franchise_id,
            {
                "event": "new_incoming_trip_sheet",
                "trip_sheet_id": trip_sheet.id,
                "from_franchise_id": franchise_id,
                "from_franchise_name": sender_name,
                "from_franchise_address":sender_address,
                "from_franchise_pincode":sender_pincode,
                "total_packages": total_packages,
                "total_freight": float(total_freight),
            }
        )

    return TripSheetResponse(
        id=trip_sheet.id,
        destination_franchise_id=data.destination_franchise_id,
        route_franchise_ids=data.route_franchise_ids,
        is_local=data.is_local,
        route_city=data.route_city,
        destination_city=data.destination_city,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        items=items,
        topay_freight=topay_freight,
        topay_packages=topay_packages,
        credit_freight=credit_freight,
        credit_packages=credit_packages,
        cod_freight=cod_freight,
        cod_packages=cod_packages,
        prepaid_freight=prepaid_freight,
        prepaid_packages=prepaid_packages,
        total_freight=total_freight,
        total_packages=total_packages
    )

async def update_trip_sheet(db: AsyncSession, trip_sheet_id: str, data: "TripSheetRequest", current_user: User):
    from app.schemas.operations import TripSheetResponse, TripSheetItem
    from app.models.trip_sheet import TripSheet, TripSheetOrder
    
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    filters = [TripSheet.id == trip_sheet_id]
    if franchise_id:
        filters.append(TripSheet.franchise_id == franchise_id)
    elif warehouse_id:
        filters.append(TripSheet.warehouse_id == warehouse_id)

    query = select(TripSheet).where(and_(*filters))
    trip_sheet = (await db.execute(query)).scalar_one_or_none()
    if not trip_sheet:
        raise HTTPException(status_code=404, detail="Trip sheet not found")

    order_filters = [Order.order_number.in_(data.barcodes)]
    if franchise_id:
        order_filters.append(Order.franchise_id == franchise_id)
    elif warehouse_id:
        order_filters.append(Order.warehouse_id == warehouse_id)

    orders = (await db.execute(select(Order).where(and_(*order_filters)))).scalars().all()
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found for given barcodes under your franchise/warehouse")

    found_numbers = {o.order_number for o in orders}
    missing = [b for b in data.barcodes if b not in found_numbers]
    if missing:
        raise HTTPException(
            status_code=403,
            detail=f"The following orders are not under your franchise/warehouse or do not exist: {missing}"
        )

    # Delete old orders manually if cascade delete-orphan relies on modifying the collection
    await db.execute(delete(TripSheetOrder).where(TripSheetOrder.trip_sheet_id == trip_sheet_id))

    items = []
    topay_freight = 0.0
    topay_packages = 0
    credit_freight = 0.0
    credit_packages = 0
    cod_freight = 0.0
    cod_packages = 0
    prepaid_freight = 0.0
    prepaid_packages = 0
    total_freight = 0.0
    total_packages = 0
    
    trip_sheet_orders = []
    
    for idx, order in enumerate(orders, start=1):
        freight = float(order.total_freight or 0)
        boxes = int(order.total_boxes or 0)
        if boxes == 0:
            boxes = 1
            
        payment = str(order.payment_method).lower().replace(" ", "")
        if payment == "topay":
            topay_freight += freight
            topay_packages += boxes
        elif payment == "credit":
            credit_freight += freight
            credit_packages += boxes
        elif payment == "cod":
            cod_freight += freight
            cod_packages += boxes
        elif payment == "prepaid":
            prepaid_freight += freight
            prepaid_packages += boxes
            
        total_freight += freight
        total_packages += boxes
        
        items.append(TripSheetItem(
            sl_no=idx,
            order_id=order.id,
            order_number=order.order_number,
            payment_method=order.payment_method,
            total_freight=freight,
            total_boxes=boxes
        ))
        
        trip_sheet_orders.append(
            TripSheetOrder(
                trip_sheet_id=trip_sheet_id,
                order_id=order.id,
                sl_no=idx
            )
        )

    trip_sheet.destination_franchise_id = data.destination_franchise_id
    trip_sheet.route_franchise_ids = data.route_franchise_ids
    trip_sheet.is_local = data.is_local
    trip_sheet.route_city = data.route_city
    trip_sheet.destination_city = data.destination_city
    trip_sheet.driver_id = data.driver_id
    trip_sheet.vehicle_id = data.vehicle_id
    trip_sheet.topay_freight = topay_freight
    trip_sheet.topay_packages = topay_packages
    trip_sheet.credit_freight = credit_freight
    trip_sheet.credit_packages = credit_packages
    trip_sheet.cod_freight = cod_freight
    trip_sheet.cod_packages = cod_packages
    trip_sheet.prepaid_freight = prepaid_freight
    trip_sheet.prepaid_packages = prepaid_packages
    trip_sheet.total_freight = total_freight
    trip_sheet.total_packages = total_packages
    
    db.add_all(trip_sheet_orders)
    await db.flush()

    return TripSheetResponse(
        id=trip_sheet.id,
        destination_franchise_id=data.destination_franchise_id,
        route_franchise_ids=data.route_franchise_ids,
        is_local=data.is_local,
        route=data.route,
        destination=data.destination,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        items=items,
        topay_freight=topay_freight,
        topay_packages=topay_packages,
        credit_freight=credit_freight,
        credit_packages=credit_packages,
        cod_freight=cod_freight,
        cod_packages=cod_packages,
        prepaid_freight=prepaid_freight,
        prepaid_packages=prepaid_packages,
        total_freight=total_freight,
        total_packages=total_packages
    )

async def delete_trip_sheet(db: AsyncSession, trip_sheet_id: str, current_user: User):
    from app.models.trip_sheet import TripSheet
    
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    filters = [TripSheet.id == trip_sheet_id]
    if franchise_id:
        filters.append(TripSheet.franchise_id == franchise_id)
    elif warehouse_id:
        filters.append(TripSheet.warehouse_id == warehouse_id)

    query = select(TripSheet).where(and_(*filters))
    trip_sheet = (await db.execute(query)).scalar_one_or_none()
    if not trip_sheet:
        raise HTTPException(status_code=404, detail="Trip sheet not found")
        
    await db.delete(trip_sheet)
    await db.commit()

async def get_trip_sheet_drivers(db: AsyncSession, current_user: User, name: Optional[str] = None, phone: Optional[str] = None):
    from app.modules.fleet.models.driver import Driver
    from app.schemas.operations import TripSheetDriverOut
    from sqlalchemy import or_
    
    from app.modules.fleet.services.fleet_management_service import _resolve_franchise_id as _fm_resolve_franchise, _resolve_warehouse_id as _fm_resolve_warehouse, _apply_driver_scope
    
    fm_franchise_id = await _fm_resolve_franchise(db, current_user)
    fm_warehouse_id = await _fm_resolve_warehouse(db, current_user)
    
    filters = []
    
    if name:
        filters.append(or_(Driver.first_name.ilike(f"%{name}%"), Driver.last_name.ilike(f"%{name}%")))
    if phone:
        filters.append(Driver.phone.ilike(f"%{phone}%"))
        
    query = select(Driver)
    if filters:
        query = query.where(and_(*filters))
    
    query = _apply_driver_scope(query, fm_franchise_id, fm_warehouse_id)
        
    drivers = (await db.execute(query)).scalars().all()
    return [TripSheetDriverOut.model_validate(d) for d in drivers]


async def get_trip_sheet_vehicles(db: AsyncSession, current_user: User, plate_number: Optional[str] = None, model: Optional[str] = None):
    from app.modules.fleet.models.vehicle import Vehicle
    from app.schemas.operations import TripSheetVehicleOut
    
    from app.modules.fleet.services.fleet_management_service import _resolve_franchise_id as _fm_resolve_franchise, _resolve_warehouse_id as _fm_resolve_warehouse, _apply_vehicle_scope
    
    fm_franchise_id = await _fm_resolve_franchise(db, current_user)
    fm_warehouse_id = await _fm_resolve_warehouse(db, current_user)
    
    filters = []
        
    if plate_number:
        filters.append(Vehicle.plate_number.ilike(f"%{plate_number}%"))
    if model:
        filters.append(Vehicle.model.ilike(f"%{model}%"))
        
    query = select(Vehicle)
    if filters:
        query = query.where(and_(*filters))
        
    query = _apply_vehicle_scope(query, fm_franchise_id, fm_warehouse_id)
        
    vehicles = (await db.execute(query)).scalars().all()
    return [TripSheetVehicleOut.model_validate(v) for v in vehicles]


async def get_trip_sheet_franchises(db: AsyncSession, current_user: User, name: Optional[str] = None, pincode: Optional[str] = None, permanent_address: Optional[str] = None):
    from app.models.franchise import Franchise
    from app.schemas.operations import TripSheetFranchiseOut
    
    filters = []
    if name:
        filters.append(Franchise.name.ilike(f"%{name}%"))
    if pincode:
        filters.append(Franchise.pincode.ilike(f"%{pincode}%"))
    if permanent_address:
        filters.append(Franchise.permanent_address.ilike(f"%{permanent_address}%"))
    
    # We should return all franchises to allow choosing a destination
    query = select(Franchise)
    if filters:
        query = query.where(and_(*filters))
        
    franchises = (await db.execute(query)).scalars().all()
    
    return [TripSheetFranchiseOut.model_validate(f) for f in franchises]

async def scan_order_for_trip_sheet(db: AsyncSession, current_user: User, barcode: str):
    from app.models.order import Order
    from app.schemas.order import OrderOut
    from sqlalchemy.orm import selectinload
    
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)
    
    filters = [Order.order_number == barcode]
    if franchise_id:
        filters.append(Order.franchise_id == franchise_id)
    elif warehouse_id:
        filters.append(Order.warehouse_id == warehouse_id)
        
    query = (
        select(Order)
        .options(
            selectinload(Order.pickup_address),
            selectinload(Order.consignee),
            selectinload(Order.items),
            selectinload(Order.packages),
            selectinload(Order.franchise),
            selectinload(Order.creator)
        )
        .where(and_(*filters))
    )
    order = (await db.execute(query)).scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or does not belong to your franchise/warehouse")
        
    return OrderOut.model_validate(order)

async def list_trip_sheets(
    db: AsyncSession, 
    current_user: User, 
    page: int, 
    limit: int
) -> dict:
    from app.models.trip_sheet import TripSheet
    from app.schemas.operations import TripSheetListOut
    import math
    
    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)
    
    filters = []
    if franchise_id:
        filters.append(TripSheet.franchise_id == franchise_id)
    elif warehouse_id:
        filters.append(TripSheet.warehouse_id == warehouse_id)
        
    total_query = select(func.count()).select_from(TripSheet)
    if filters:
        total_query = total_query.where(and_(*filters))
    total = (await db.execute(total_query)).scalar_one()
    
    query = select(TripSheet)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(TripSheet.created_at.desc()).offset((page - 1) * limit).limit(limit)
    
    rows = (await db.execute(query)).scalars().all()
    
    return {
        "items": [TripSheetListOut.model_validate(row) for row in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0
    }

async def get_trip_sheet_by_id(db: AsyncSession, current_user: User, trip_sheet_id: str):
    from app.models.trip_sheet import TripSheet
    from app.models.franchise import Franchise
    from app.models.order import Order
    from app.schemas.operations import (
        TripSheetDetailOut, TripSheetOrderDetailOut,
        TripSheetPickupAddressOut, TripSheetConsigneeOut,
        TripSheetFranchiseOut, TripSheetDriverOut, TripSheetVehicleOut,
        TripSheetRouteFranchiseOut
    )

    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    # A trip sheet is accessible if:
    # 1. The user created it (franchise_id or warehouse_id matches), OR
    # 2. The user's franchise is the destination franchise
    from sqlalchemy import or_
    access_filter = TripSheet.id == trip_sheet_id
    if franchise_id:
        access_filter = and_(
            TripSheet.id == trip_sheet_id,
            or_(
                TripSheet.franchise_id == franchise_id,
                TripSheet.destination_franchise_id == franchise_id
            )
        )
    elif warehouse_id:
        access_filter = and_(
            TripSheet.id == trip_sheet_id,
            TripSheet.warehouse_id == warehouse_id
        )

    query = select(TripSheet).where(access_filter)
    trip_sheet = (await db.execute(query)).scalar_one_or_none()

    if not trip_sheet:
        raise HTTPException(status_code=404, detail="Trip sheet not found")

    # Load full route franchises with seq_no
    route_franchises = []
    if trip_sheet.route_franchise_ids:
        fids = trip_sheet.route_franchise_ids
        f_rows = (await db.execute(select(Franchise).where(Franchise.id.in_(fids)))).scalars().all()
        f_map = {f.id: f for f in f_rows}
        route_franchises = [
            TripSheetRouteFranchiseOut(
                seq_no=idx,
                id=f_map[fid].id,
                name=f_map[fid].name,
                franchise_code=f_map[fid].franchise_code,
                email=f_map[fid].email,
                phone=f_map[fid].phone,
                latitude=f_map[fid].latitude,
                longitude=f_map[fid].longitude,
                proposed_location=f_map[fid].proposed_location,
                permanent_address=f_map[fid].permanent_address,
                date_of_birth=f_map[fid].date_of_birth,
                
            )
            for idx, fid in enumerate(fids, start=1) if fid in f_map
        ]


    # Build enriched order items
    order_details = []
    for trip_order in trip_sheet.orders:
        order: Order = trip_order.order
        pickup = None
        consignee = None
        if order:
            if order.pickup_address:
                pickup = TripSheetPickupAddressOut.model_validate(order.pickup_address)
            if order.consignee:
                consignee = TripSheetConsigneeOut.model_validate(order.consignee)

        order_details.append(TripSheetOrderDetailOut(
            id=trip_order.id,
            order_id=trip_order.order_id,
            sl_no=trip_order.sl_no,
            order_number=order.order_number if order else None,
            payment_method=order.payment_method if order else None,
            total_freight=float(order.total_freight) if order else None,
            total_boxes=order.total_boxes if order else None,
            pickup_address=pickup,
            consignee=consignee,
        ))

    return TripSheetDetailOut(
        id=trip_sheet.id,
        franchise_id=trip_sheet.franchise_id,
        warehouse_id=trip_sheet.warehouse_id,
        destination_franchise_id=trip_sheet.destination_franchise_id,
        route_franchise_ids=trip_sheet.route_franchise_ids,
        is_local=trip_sheet.is_local,
        route_city=trip_sheet.route_city,
        destination_city=trip_sheet.destination_city,
        driver_id=trip_sheet.driver_id,
        vehicle_id=trip_sheet.vehicle_id,
        topay_freight=float(trip_sheet.topay_freight),
        topay_packages=trip_sheet.topay_packages,
        credit_freight=float(trip_sheet.credit_freight),
        credit_packages=trip_sheet.credit_packages,
        cod_freight=float(trip_sheet.cod_freight),
        cod_packages=trip_sheet.cod_packages,
        prepaid_freight=float(trip_sheet.prepaid_freight),
        prepaid_packages=trip_sheet.prepaid_packages,
        total_freight=float(trip_sheet.total_freight),
        total_packages=trip_sheet.total_packages,
        created_at=trip_sheet.created_at,
        driver=TripSheetDriverOut.model_validate(trip_sheet.driver) if trip_sheet.driver else None,
        vehicle=TripSheetVehicleOut.model_validate(trip_sheet.vehicle) if trip_sheet.vehicle else None,
        destination_franchise=TripSheetFranchiseOut.model_validate(trip_sheet.destination_franchise) if trip_sheet.destination_franchise else None,
        franchise=TripSheetFranchiseOut.model_validate(trip_sheet.franchise) if trip_sheet.franchise else None,
        route_franchises=route_franchises,
        orders=order_details,
    )


async def list_incoming_trip_sheets(
    db: AsyncSession,
    current_user: User,
    page: int,
    limit: int
) -> dict:
    """
    Returns trip sheets where the current user's franchise is the DESTINATION franchise.
    These are trip sheets sent TO this franchise from another franchise/warehouse.
    """
    from app.models.trip_sheet import TripSheet
    from app.schemas.operations import TripSheetListOut
    import math

    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    filters = []
    if franchise_id:
        filters.append(TripSheet.destination_franchise_id == franchise_id)
    elif warehouse_id:
        # A warehouse doesn't receive "incoming" trip sheets in the same way,
        # but if we needed to filter for them, we would.
        # For now, return an empty list or filter to impossible condition
        # if warehouses shouldn't see anything here.
        filters.append(TripSheet.destination_franchise_id == "impossible_for_warehouse")

    # If both franchise_id and warehouse_id are None, it's a global admin.
    # They see all trip sheets (or all that have a destination).
    if not franchise_id and not warehouse_id:
        filters.append(TripSheet.destination_franchise_id.isnot(None))

    total_query = select(func.count()).select_from(TripSheet)
    if filters:
        total_query = total_query.where(and_(*filters))
    total = (await db.execute(total_query)).scalar() or 0

    offset = (page - 1) * limit
    query = select(TripSheet)
    if filters:
        query = query.where(and_(*filters))
    
    query = (
        query.order_by(TripSheet.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    trip_sheets = (await db.execute(query)).scalars().all()

    items = [TripSheetListOut.model_validate(ts) for ts in trip_sheets]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0
    }
