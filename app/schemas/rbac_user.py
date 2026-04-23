from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    pincode: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    pincode: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class RoleInfo(BaseModel):
    id: str
    name: str


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    pincode: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    franchise_id: Optional[str] = None
    employee_code: Optional[str] = None
    role: Optional[RoleInfo] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    limit: int
    pages: int


class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str
