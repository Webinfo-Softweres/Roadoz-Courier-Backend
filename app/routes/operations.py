from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.role_checker import get_current_user, require_permission
from app.models.user import User
from app.schemas.operations import (
    AttendanceCreate,
    CashVoucherCreate,
    ExpenseCreate,
    ManifestCreate,
    PodCreate,
    TripSheetRequest,
)
from app.services.operations_service import (
    create_attendance,
    create_cash_voucher,
    create_expense,
    create_manifest,
    create_pod,
    get_pod_by_order,
    list_attendance,
    list_cash_vouchers,
    list_expenses,
    list_manifests,
)

router = APIRouter(prefix="/operations", tags=["Operations"])


@router.post("/expenses", status_code=201)
async def create_expense_endpoint(data: ExpenseCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _: User = Depends(require_permission("users:manage"))):
    return await create_expense(db, data, current_user)


@router.get("/expenses")
async def list_expenses_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    franchise_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("users:manage")),
):
    return await list_expenses(db, current_user, page, limit, date_from, date_to, franchise_id)


@router.post("/cash-vouchers", status_code=201)
async def create_cash_voucher_endpoint(data: CashVoucherCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _: User = Depends(require_permission("users:manage"))):
    return await create_cash_voucher(db, data, current_user)


@router.get("/cash-vouchers")
async def list_cash_vouchers_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    franchise_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("users:manage")),
):
    return await list_cash_vouchers(db, current_user, page, limit, date_from, date_to, franchise_id)


@router.post("/attendance", status_code=201)
async def create_attendance_endpoint(data: AttendanceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _: User = Depends(require_permission("users:view"))):
    return await create_attendance(db, data, current_user)


@router.get("/attendance")
async def list_attendance_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    attendance_date: date | None = Query(None),
    franchise_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("users:view")),
):
    return await list_attendance(db, current_user, page, limit, attendance_date, franchise_id)


@router.post("/manifests", status_code=201)
async def create_manifest_endpoint(data: ManifestCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _: User = Depends(require_permission("orders:create"))):
    return await create_manifest(db, data, current_user)


@router.get("/manifests")
async def list_manifests_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    manifest_date: date | None = Query(None),
    franchise_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("orders:view")),
):
    return await list_manifests(db, current_user, page, limit, manifest_date, franchise_id)


@router.post("/pods", status_code=201)
async def create_pod_endpoint(data: PodCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _: User = Depends(require_permission("orders:create"))):
    return await create_pod(db, data, current_user)


@router.get("/pods/order/{order_id}")
async def get_pod_by_order_endpoint(order_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), _: User = Depends(require_permission("orders:view"))):
    return await get_pod_by_order(db, order_id, current_user)


@router.post("/trip-sheet", status_code=200)
async def generate_trip_sheet_endpoint(
    data: TripSheetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:create"))
):
    from app.services.operations_service import generate_trip_sheet
    return await generate_trip_sheet(db, data, current_user)

@router.get("/trip-sheet/drivers")
async def get_trip_sheet_drivers_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:create"))
):
    from app.services.operations_service import get_trip_sheet_drivers
    return await get_trip_sheet_drivers(db, current_user)

@router.get("/trip-sheet/vehicles")
async def get_trip_sheet_vehicles_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:create"))
):
    from app.services.operations_service import get_trip_sheet_vehicles
    return await get_trip_sheet_vehicles(db, current_user)

@router.get("/trip-sheet/franchises")
async def get_trip_sheet_franchises_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:create"))
):
    from app.services.operations_service import get_trip_sheet_franchises
    return await get_trip_sheet_franchises(db, current_user)

@router.get("/trip-sheet")
async def list_trip_sheets_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:create"))
):
    from app.services.operations_service import list_trip_sheets
    return await list_trip_sheets(db, current_user, page, limit)

@router.get("/trip-sheet/{trip_sheet_id}")
async def get_trip_sheet_by_id_endpoint(
    trip_sheet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:create"))
):
    from app.services.operations_service import get_trip_sheet_by_id
    return await get_trip_sheet_by_id(db, current_user, trip_sheet_id)

@router.put("/trip-sheet/{trip_sheet_id}")
async def update_trip_sheet_endpoint(
    trip_sheet_id: str,
    data: TripSheetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:update"))
):
    from app.services.operations_service import update_trip_sheet
    return await update_trip_sheet(db, trip_sheet_id, data, current_user)

@router.delete("/trip-sheet/{trip_sheet_id}")
async def delete_trip_sheet_endpoint(
    trip_sheet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("tripsheet:delete"))
):
    from app.services.operations_service import delete_trip_sheet
    await delete_trip_sheet(db, trip_sheet_id, current_user)
    return {"message": "Trip sheet deleted successfully"}
