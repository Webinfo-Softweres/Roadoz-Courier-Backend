import os
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.fleet_file import FleetFile

UPLOAD_DIR = "uploads/fleet"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = {"vehicle_insurance", "license_front", "license_back"}


def _validate_document_type(document_type: str) -> None:
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid documentType. Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_TYPES))}",
        )


def _validate_file(file: UploadFile) -> None:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size too large. Maximum is 5MB")


async def upload_driver_document(
    db: AsyncSession,
    driver: Driver,
    document_type: str,
    file: UploadFile,
) -> str:
    _validate_document_type(document_type)
    _validate_file(file)

    ext = os.path.splitext(file.filename or "")[1].lower()
    rel_dir = f"{UPLOAD_DIR}/{driver.id}"
    Path(rel_dir).mkdir(parents=True, exist_ok=True)
    filename = f"{document_type}{ext}"
    disk_path = os.path.join(rel_dir, filename)
    url_path = f"/{rel_dir}/{filename}"

    with open(disk_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = await db.execute(
        select(FleetFile).where(
            FleetFile.subject_type == "driver",
            FleetFile.subject_id == driver.id,
            FleetFile.document_type == document_type,
        )
    )
    existing = result.scalar_one_or_none()
    file.file.seek(0, 2)
    file_size = file.file.tell()

    if existing:
        if os.path.exists(existing.path.lstrip("/")):
            try:
                os.remove(existing.path.lstrip("/"))
            except OSError:
                pass
        existing.path = url_path
        existing.content_type = file.content_type
        existing.file_size = file_size
        existing.original_filename = file.filename
    else:
        db.add(
            FleetFile(
                subject_type="driver",
                subject_id=driver.id,
                document_type=document_type,
                path=url_path,
                content_type=file.content_type,
                file_size=file_size,
                original_filename=file.filename,
            )
        )

    if driver.onboarding_status == "rejected":
        driver.onboarding_status = "incomplete"
        driver.rejection_reason = None

    await db.flush()
    return url_path


async def get_driver_documents(db: AsyncSession, driver_id: str) -> list[FleetFile]:
    result = await db.execute(
        select(FleetFile).where(FleetFile.subject_type == "driver", FleetFile.subject_id == driver_id)
    )
    return list(result.scalars().all())
