from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RemittanceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    REMITTED = "remitted"


# ── Summary (dashboard card) ─────────────────────────────────────────────


class RemittanceSummaryOut(BaseModel):
    remitted_till_date: float
    remitted_orders: int
    due_amount: float
    due_orders: int


# ── Remittance Order detail ──────────────────────────────────────────────


class RemittanceOrderOut(BaseModel):
    id: str
    order_id: str
    cod_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Remittance ───────────────────────────────────────────────────────────


class RemittanceOut(BaseModel):
    id: str
    franchise_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    total_amount: float
    orders_count: int
    status: str
    reference_number: Optional[str] = None
    remarks: Optional[str] = None
    remitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    orders: List[RemittanceOrderOut] = []

    model_config = {"from_attributes": True}


class RemittanceListResponse(BaseModel):
    items: List[RemittanceOut]
    total: int
    page: int
    limit: int
    pages: int


# ── Requests ─────────────────────────────────────────────────────────────


class RemittanceCreateRequest(BaseModel):
    franchise_id: str = Field(..., description="Franchise to create remittance for")
    order_ids: List[str] = Field(..., min_length=1, description="List of delivered COD order IDs to include")
    remarks: Optional[str] = Field(None, max_length=500)


class RemittanceMarkRemittedRequest(BaseModel):
    reference_number: Optional[str] = Field(None, max_length=100, description="Bank transfer reference")
    remarks: Optional[str] = Field(None, max_length=500)
