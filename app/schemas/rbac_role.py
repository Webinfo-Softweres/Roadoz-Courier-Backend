from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RoleCreateRequest(BaseModel):
    name: str
    permission_codes: list[str] = []


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    permission_codes: Optional[list[str]] = None


class RoleOut(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleWithPermissionsOut(RoleOut):
    permissions: list[str] = []


class RoleListResponse(BaseModel):
    items: list[RoleWithPermissionsOut]
    total: int
    page: int
    limit: int
    pages: int
