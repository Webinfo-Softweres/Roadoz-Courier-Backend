from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class MonthEndClosingBase(BaseModel):
    transaction_id: str
    bank_name: str
    bank_owner_name: str
    bank_account_number: Optional[str] = None


class MonthEndClosingCreate(MonthEndClosingBase):
    pass


class MonthEndClosingUpdateStatus(BaseModel):
    status: str  # "approved" or "rejected"
    admin_notes: Optional[str] = None


class MonthEndClosingResponse(MonthEndClosingBase):
    id: str
    franchise_id: str
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonthEndClosingList(BaseModel):
    data: list[MonthEndClosingResponse]
    total: int
    page: int
    size: int
