"""Trip sheet driver mobile API tests."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.trip_sheet import TripSheet
from app.models.user import User
from app.modules.fleet.constants import SHEET_STATUS_PENDING_ACCEPT
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.services.trip_sheet_lifecycle import apply_driver_assignment_to_trip_sheet
from app.tests.test_fleet_onboarding import _auth_headers, _register_driver


@pytest.mark.asyncio
async def test_apply_driver_assignment_sets_pending_accept():
    sheet = TripSheet(
        id=str(uuid.uuid4()),
        franchise_id=None,
        warehouse_id=None,
        is_local=False,
        topay_freight=0,
        topay_packages=0,
        credit_freight=0,
        credit_packages=0,
        cod_freight=0,
        cod_packages=0,
        prepaid_freight=0,
        prepaid_packages=0,
        total_freight=0,
        total_packages=0,
        created_by=str(uuid.uuid4()),
    )
    driver_id = str(uuid.uuid4())
    apply_driver_assignment_to_trip_sheet(sheet, driver_id, reset=True)
    assert sheet.driver_id == driver_id
    assert sheet.driver_status == SHEET_STATUS_PENDING_ACCEPT


@pytest.mark.asyncio
async def test_driver_list_new_trips_when_online():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await _register_driver(client)
        token = reg["token"]
        async with AsyncSessionLocal() as db:
            driver = (
                await db.execute(select(Driver).where(Driver.user_id == reg["userId"]))
            ).scalar_one()
            driver.onboarding_status = "approved"
            driver.online = True
            admin = (await db.execute(select(User).limit(1))).scalar_one()
            sheet = TripSheet(
                id=str(uuid.uuid4()),
                franchise_id=None,
                warehouse_id=None,
                is_local=True,
                destination_city="Kochi",
                driver_id=driver.id,
                topay_freight=0,
                topay_packages=1,
                credit_freight=0,
                credit_packages=0,
                cod_freight=0,
                cod_packages=0,
                prepaid_freight=100,
                prepaid_packages=1,
                total_freight=100,
                total_packages=1,
                created_by=admin.id,
            )
            apply_driver_assignment_to_trip_sheet(sheet, driver.id, reset=True)
            db.add(sheet)
            await db.commit()

        response = await client.get("/api/v1/driver/trips/new", headers=_auth_headers(token))
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
