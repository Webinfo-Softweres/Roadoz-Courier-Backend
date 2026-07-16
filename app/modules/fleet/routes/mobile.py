from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.fleet.dependencies.require_driver import require_driver
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.schemas.onboard import (
    BankDetailsRequest,
    RegisterRequest,
    RegisterResponse,
    StatusResponse,
    SuccessMessageResponse,
    UploadDocumentResponse,
    VehicleRequest,
)
from app.modules.fleet.services.file_service import upload_driver_document
from app.modules.fleet.services.onboard_service import (
    get_onboarding_status,
    register_driver,
    submit_bank_details,
)
from app.modules.fleet.services.vehicle_service import upsert_driver_vehicle

auth_router = APIRouter(prefix="/api/auth", tags=["Driver Auth"])
driver_router = APIRouter(prefix="/api/driver", tags=["Driver Onboarding"])
router = APIRouter()


@auth_router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_driver(db, payload)


@driver_router.post("/vehicle", response_model=SuccessMessageResponse)
async def save_vehicle(
    payload: VehicleRequest,
    driver: Driver = Depends(require_driver),
    db: AsyncSession = Depends(get_db),
):
    if driver.onboarding_status == "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already approved")
    if driver.onboarding_status == "pending_verification":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already submitted")

    await upsert_driver_vehicle(db, driver, payload)
    return SuccessMessageResponse(message="Vehicle details recorded successfully.")


@driver_router.post("/upload-document", response_model=UploadDocumentResponse)
async def upload_document(
    documentType: str = Form(...),
    file: UploadFile = File(...),
    driver: Driver = Depends(require_driver),
    db: AsyncSession = Depends(get_db),
):
    if driver.onboarding_status == "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already approved")
    if driver.onboarding_status == "pending_verification":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already submitted")

    url = await upload_driver_document(db, driver, documentType, file)
    return UploadDocumentResponse(documentUrl=url)


@driver_router.post("/bank-details", response_model=SuccessMessageResponse)
async def save_bank_details(
    payload: BankDetailsRequest,
    driver: Driver = Depends(require_driver),
    db: AsyncSession = Depends(get_db),
):
    await submit_bank_details(db, driver, payload)
    return SuccessMessageResponse(message="Onboarding details submitted for verification.")


@driver_router.get("/status", response_model=StatusResponse)
async def onboarding_status(
    driver: Driver = Depends(require_driver),
    db: AsyncSession = Depends(get_db),
):
    return await get_onboarding_status(db, driver)


router.include_router(auth_router)
router.include_router(driver_router)
