from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fleet.models.driver import Driver
from app.modules.fleet.models.vehicle import Vehicle
from app.modules.fleet.schemas.onboard import VehicleRequest


async def upsert_driver_vehicle(db: AsyncSession, driver: Driver, data: VehicleRequest) -> Vehicle:
    vehicle = driver.vehicle
    if not vehicle:
        vehicle = Vehicle(
            type=data.vehicleType,
            plate_number=data.registrationNumber,
            make=data.make,
            model=data.model,
            year=data.year,
            color=data.color,
            status="draft",
        )
        db.add(vehicle)
        await db.flush()
        driver.vehicle_id = vehicle.id
    else:
        vehicle.type = data.vehicleType
        vehicle.plate_number = data.registrationNumber
        vehicle.make = data.make
        vehicle.model = data.model
        vehicle.year = data.year
        vehicle.color = data.color

    if driver.onboarding_status == "rejected":
        driver.onboarding_status = "incomplete"
        driver.rejection_reason = None

    await db.flush()
    return vehicle
