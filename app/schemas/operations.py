from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    expense_date: date
    expense_head: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    approved_by: Optional[str] = None
    remarks: Optional[str] = Field(None, max_length=500)


class ExpenseOut(BaseModel):
    id: str
    franchise_id: Optional[str]
    warehouse_id: Optional[str] = None
    expense_date: date
    expense_head: str
    amount: float
    approved_by: Optional[str]
    remarks: Optional[str]
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CashVoucherCreate(BaseModel):
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    voucher_date: date
    type: str = Field(..., pattern="^(debit|credit)$")
    amount: float = Field(..., gt=0)
    payment_mode: str = Field("Cash", max_length=30)
    description: str = Field(..., min_length=1, max_length=500)


class CashVoucherOut(BaseModel):
    id: str
    voucher_no: str
    franchise_id: Optional[str]
    warehouse_id: Optional[str] = None
    voucher_date: date
    type: str
    amount: float
    payment_mode: str
    description: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceCreate(BaseModel):
    user_id: str
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    attendance_date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str = Field("present", pattern="^(present|absent|half_day|leave)$")
    remarks: Optional[str] = Field(None, max_length=500)


class AttendanceOut(BaseModel):
    id: str
    user_id: str
    franchise_id: Optional[str]
    attendance_date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    status: str
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ManifestCreate(BaseModel):
    franchise_id: Optional[str] = None
    manifest_date: date
    vehicle_no: Optional[str] = Field(None, max_length=50)
    route: Optional[str] = Field(None, max_length=150)
    order_ids: List[str] = Field(..., min_length=1)


class ManifestOrderOut(BaseModel):
    id: str
    order_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ManifestOut(BaseModel):
    id: str
    manifest_no: str
    franchise_id: Optional[str]
    manifest_date: date
    vehicle_no: Optional[str]
    route: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    orders: List[ManifestOrderOut] = []

    model_config = {"from_attributes": True}


class PodCreate(BaseModel):
    order_id: str
    receiver_name: str = Field(..., min_length=1, max_length=150)
    received_at: datetime
    delivery_staff_id: Optional[str] = None
    otp_verified: bool = False
    signature_url: Optional[str] = None
    remarks: Optional[str] = Field(None, max_length=500)


class PodOut(BaseModel):
    id: str
    order_id: str
    receiver_name: str
    received_at: datetime
    delivery_staff_id: Optional[str]
    otp_verified: bool
    signature_url: Optional[str]
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    expense_date: date
    expense_head: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    approved_by: Optional[str] = None
    remarks: Optional[str] = Field(None, max_length=500)


class ExpenseOut(BaseModel):
    id: str
    franchise_id: Optional[str]
    warehouse_id: Optional[str] = None
    expense_date: date
    expense_head: str
    amount: float
    approved_by: Optional[str]
    remarks: Optional[str]
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CashVoucherCreate(BaseModel):
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    voucher_date: date
    type: str = Field(..., pattern="^(debit|credit)$")
    amount: float = Field(..., gt=0)
    payment_mode: str = Field("Cash", max_length=30)
    description: str = Field(..., min_length=1, max_length=500)


class CashVoucherOut(BaseModel):
    id: str
    voucher_no: str
    franchise_id: Optional[str]
    warehouse_id: Optional[str] = None
    voucher_date: date
    type: str
    amount: float
    payment_mode: str
    description: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceCreate(BaseModel):
    user_id: str
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    attendance_date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str = Field("present", pattern="^(present|absent|half_day|leave)$")
    remarks: Optional[str] = Field(None, max_length=500)


class AttendanceOut(BaseModel):
    id: str
    user_id: str
    franchise_id: Optional[str]
    attendance_date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    status: str
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ManifestCreate(BaseModel):
    franchise_id: Optional[str] = None
    manifest_date: date
    vehicle_no: Optional[str] = Field(None, max_length=50)
    route: Optional[str] = Field(None, max_length=150)
    order_ids: List[str] = Field(..., min_length=1)


class ManifestOrderOut(BaseModel):
    id: str
    order_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ManifestOut(BaseModel):
    id: str
    manifest_no: str
    franchise_id: Optional[str]
    manifest_date: date
    vehicle_no: Optional[str]
    route: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    orders: List[ManifestOrderOut] = []

    model_config = {"from_attributes": True}


class PodCreate(BaseModel):
    order_id: str
    receiver_name: str = Field(..., min_length=1, max_length=150)
    received_at: datetime
    delivery_staff_id: Optional[str] = None
    otp_verified: bool = False
    signature_url: Optional[str] = None
    remarks: Optional[str] = Field(None, max_length=500)


class PodOut(BaseModel):
    id: str
    order_id: str
    receiver_name: str
    received_at: datetime
    delivery_staff_id: Optional[str]
    otp_verified: bool
    signature_url: Optional[str]
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TripSheetRequest(BaseModel):
    barcodes: List[str] = Field(..., min_length=1)
    destination_franchise_id: Optional[str] = None
    route_franchise_ids: Optional[List[str]] = []
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    is_local: bool = False
    route_city: Optional[List[str]] = []
    destination_city: Optional[str] = None

class TripSheetItem(BaseModel):
    sl_no: int
    order_id: str
    order_number: str
    payment_method: str
    total_freight: float
    total_boxes: int

class TripSheetResponse(BaseModel):
    id: str
    destination_franchise_id: Optional[str] = None
    route_franchise_ids: Optional[List[str]] = []
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    is_local: bool = False
    route_city: Optional[List[str]] = []
    destination_city: Optional[str] = None
    items: List[TripSheetItem]
    topay_freight: float
    topay_packages: int
    credit_freight: float
    credit_packages: int
    cod_freight: float
    cod_packages: int
    prepaid_freight: float
    prepaid_packages: int
    total_freight: float
    total_packages: int

class TripSheetDriverOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}

class TripSheetVehicleOut(BaseModel):
    id: str
    plate_number: str
    make: str
    model: str
    type: str

    model_config = {"from_attributes": True}

class TripSheetFranchiseOut(BaseModel):
    id: str
    name: str
    # franchise_code: str
    email: str
    phone: Optional[str] = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    proposed_location:str
    permanent_address:str
    date_of_birth: date
    model_config = {"from_attributes": True}

class TripSheetListOut(BaseModel):
    id: str
    franchise_id: Optional[str]
    warehouse_id: Optional[str]
    destination_franchise_id: Optional[str]
    driver_id: Optional[str]
    vehicle_id: Optional[str]
    total_freight: float
    total_packages: int
    created_at: datetime

    driver: Optional[TripSheetDriverOut] = None
    vehicle: Optional[TripSheetVehicleOut] = None
    destination_franchise: Optional[TripSheetFranchiseOut] = None

    model_config = {"from_attributes": True}

class TripSheetPickupAddressOut(BaseModel):
    id: str
    contact_name: str
    nickname:str
    email:str
    phone: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    pincode: str
    latitude:float | None = None
    longitude:float | None = None
    model_config = {"from_attributes": True}

class TripSheetConsigneeOut(BaseModel):
    id: str
    name: str
    mobile: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    pincode: str
    latitude:float | None = None
    longitude:float | None = None

    model_config = {"from_attributes": True}

class TripSheetOrderDetailOut(BaseModel):
    id: str
    order_id: str
    sl_no: int
    order_number: Optional[str] = None
    payment_method: Optional[str] = None
    total_freight: Optional[float] = None
    total_boxes: Optional[int] = None
    pickup_address: Optional[TripSheetPickupAddressOut] = None
    consignee: Optional[TripSheetConsigneeOut] = None

    model_config = {"from_attributes": True}

class TripSheetRouteFranchiseOut(BaseModel):
    seq_no: int
    id: str
    name: str
    franchise_code: str
    email: str
    phone: Optional[str] = None
    date_of_birth : date
    permanent_address : str
    proposed_location : str
    latitude : float| None = None
    longitude : float| None = None

    model_config = {"from_attributes": True}

class TripSheetDetailOut(BaseModel):
    id: str
    franchise_id: Optional[str]
    warehouse_id: Optional[str]
    destination_franchise_id: Optional[str]
    route_franchise_ids: Optional[List[str]]
    driver_id: Optional[str]
    vehicle_id: Optional[str]
    is_local: bool
    route_city: Optional[List[str]]
    destination_city: Optional[str]

    topay_freight: float
    topay_packages: int
    credit_freight: float
    credit_packages: int
    cod_freight: float
    cod_packages: int
    prepaid_freight: float
    prepaid_packages: int
    total_freight: float
    total_packages: int

    created_at: datetime

    driver: Optional[TripSheetDriverOut] = None
    vehicle: Optional[TripSheetVehicleOut] = None
    destination_franchise: Optional[TripSheetFranchiseOut] = None
    franchise: Optional[TripSheetFranchiseOut] = None
    route_franchises: List[TripSheetRouteFranchiseOut] = []
    orders: List[TripSheetOrderDetailOut] = []

    model_config = {"from_attributes": True}
