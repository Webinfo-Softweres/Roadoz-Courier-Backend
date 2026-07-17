import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.payout_account import DriverPayoutAccount
from app.modules.fleet.schemas.onboard import (
    BankDetailsRequest,
    DocumentSteps,
    OnboardingSteps,
    RegisterRequest,
    RegisterResponse,
    StatusResponse,
)
from app.modules.fleet.services.driver_service import documents_complete
from app.modules.fleet.services.file_service import ALLOWED_DOCUMENT_TYPES, get_driver_documents
from app.utils.jwt import create_access_token


async def _get_driver_role(db: AsyncSession) -> Role:
    result = await db.execute(
        select(Role).where(
            Role.name == "driver",
            Role.franchise_id.is_(None),
            Role.warehouse_id.is_(None),
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Driver role is not configured",
        )
    return role


async def register_driver(db: AsyncSession, data: RegisterRequest) -> RegisterResponse:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        name=f"{data.firstName} {data.lastName}",
        email=data.email,
        password_hash=get_password_hash(data.password),
        phone=data.phone,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    driver = Driver(
        user_id=user.id,
        first_name=data.firstName,
        last_name=data.lastName,
        phone=data.phone,
        dob=data.dob,
        onboarding_status="incomplete",
        status="draft",
    )
    db.add(driver)
    await db.flush()

    role = await _get_driver_role(db)
    db.add(UserRole(user_id=user.id, role_id=role.id))

    token = create_access_token(
        {
            "user_id": user.id,
            "email": user.email,
            "driver_id": driver.id,
            "role": "driver",
            "franchise_id": None,
        }
    )
    return RegisterResponse(token=token, userId=user.id)


async def _build_steps(db: AsyncSession, driver: Driver) -> OnboardingSteps:
    documents = await get_driver_documents(db, driver.id)
    uploaded = {d.document_type for d in documents}
    return OnboardingSteps(
        personal=True,
        vehicle=driver.vehicle_id is not None,
        documents=DocumentSteps(
            vehicle_insurance="vehicle_insurance" in uploaded,
            license_front="license_front" in uploaded,
            license_back="license_back" in uploaded,
        ),
        payout=driver.payout_account is not None,
    )


async def get_onboarding_status(db: AsyncSession, driver: Driver) -> StatusResponse:
    steps = await _build_steps(db, driver)
    return StatusResponse(
        status=driver.onboarding_status,
        submittedAt=driver.submitted_at,
        steps=steps,
    )


async def submit_bank_details(db: AsyncSession, driver: Driver, data: BankDetailsRequest) -> None:
    if driver.onboarding_status == "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already approved")
    if driver.onboarding_status == "pending_verification":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already submitted")

    if not driver.vehicle_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vehicle details are required")

    documents = await get_driver_documents(db, driver.id)
    if not documents_complete(documents):
        missing = sorted(ALLOWED_DOCUMENT_TYPES - {d.document_type for d in documents})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required documents: {', '.join(missing)}",
        )

    if driver.payout_account:
        payout = driver.payout_account
        payout.account_holder_name = data.accountHolderName
        payout.bank_name = data.bankName
        payout.account_number = data.accountNumber
        payout.ifsc_or_routing_code = data.ifscOrRoutingCode
    else:
        db.add(
            DriverPayoutAccount(
                driver_id=driver.id,
                account_holder_name=data.accountHolderName,
                bank_name=data.bankName,
                account_number=data.accountNumber,
                ifsc_or_routing_code=data.ifscOrRoutingCode,
            )
        )

    driver.onboarding_status = "pending_verification"
    driver.submitted_at = datetime.utcnow()
    driver.rejection_reason = None
    await db.flush()
