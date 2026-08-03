"""
Fleet driver onboarding tests.
Run with: pytest app/tests/test_fleet_onboarding.py -v
"""
import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.main import app
from app.models.franchise import Franchise
from app.models.user import User
from app.utils.jwt import decode_token


def _unique_email() -> str:
    return f"driver-{uuid.uuid4().hex[:8]}@example.com"


async def _register_driver(client: AsyncClient, email: str | None = None) -> dict:
    email = email or _unique_email()
    response = await client.post(
        "/api/auth/register",
        json={
            "firstName": "John",
            "lastName": "Doe",
            "email": email,
            "password": "SecurePassword123!",
            "dob": "1994-05-15",
            "phone": "+44 7911 123456",
        },
    )
    assert response.status_code == 201
    return response.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_returns_user_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _register_driver(client)
        uuid.UUID(data["userId"])
        assert data["token"]
        assert data["refreshToken"]


@pytest.mark.asyncio
async def test_register_refresh_round_trip_keeps_driver_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = await _register_driver(client)
        claims = decode_token(data["token"])
        assert claims["type"] == "access"
        assert claims["role"] == "driver"
        assert claims["driver_id"]

        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": data["refreshToken"]},
        )
        assert refresh_resp.status_code == 200
        body = refresh_resp.json()
        assert body["access_token"]
        assert body["refresh_token"]

        refreshed = decode_token(body["access_token"])
        assert refreshed["type"] == "access"
        assert refreshed["role"] == "driver"
        assert refreshed["driver_id"] == claims["driver_id"]
        assert refreshed["user_id"] == claims["user_id"]

        profile = await client.get(
            "/api/v1/driver/profile",
            headers=_auth_headers(body["access_token"]),
        )
        assert profile.status_code == 200
        assert profile.json()["success"] is True


@pytest.mark.asyncio
async def test_vehicle_without_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/driver/vehicle",
            json={
                "vehicleType": "Bike",
                "registrationNumber": "AB12 CDE",
                "make": "Honda",
                "model": "CB650R",
                "year": "2023",
                "color": "Red",
            },
        )
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert "message" in body


@pytest.mark.asyncio
async def test_duplicate_email_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        email = _unique_email()
        await _register_driver(client, email=email)
        response = await client.post(
            "/api/auth/register",
            json={
                "firstName": "Jane",
                "lastName": "Doe",
                "email": email,
                "password": "SecurePassword123!",
                "dob": "1994-05-15",
                "phone": "+44 7911 123456",
            },
        )
        assert response.status_code == 409
        body = response.json()
        assert body == {"success": False, "message": "Email already registered"}


@pytest.mark.asyncio
async def test_full_onboarding_flow_and_admin_approve():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await _register_driver(client)
        token = reg["token"]
        headers = _auth_headers(token)
        driver_id = decode_token(token)["driver_id"]

        vehicle_resp = await client.post(
            "/api/driver/vehicle",
            headers=headers,
            json={
                "vehicleType": "Bike",
                "registrationNumber": "AB12 CDE",
                "make": "Honda",
                "model": "CB650R",
                "year": "2023",
                "color": "Red",
            },
        )
        assert vehicle_resp.status_code == 200
        assert vehicle_resp.json()["success"] is True

        for doc_type in ("vehicle_insurance", "license_front", "license_back"):
            upload_resp = await client.post(
                "/api/driver/upload-document",
                headers=headers,
                data={"documentType": doc_type},
                files={"file": ("doc.png", io.BytesIO(b"fake-image"), "image/png")},
            )
            assert upload_resp.status_code == 200
            assert upload_resp.json()["documentUrl"].startswith("/uploads/fleet/")

        bank_resp = await client.post(
            "/api/driver/bank-details",
            headers=headers,
            json={
                "accountHolderName": "John Doe",
                "bankName": "Barclays Bank",
                "accountNumber": "12345678",
                "ifscOrRoutingCode": "20-00-00",
            },
        )
        assert bank_resp.status_code == 200
        assert bank_resp.json()["message"] == "Onboarding details submitted for verification."

        status_resp = await client.get("/api/driver/status", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "pending_verification"
        assert status_data["submittedAt"] is not None
        assert status_data["steps"]["personal"] is True
        assert status_data["steps"]["vehicle"] is True
        assert status_data["steps"]["payout"] is True

        franchise_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as db:
            owner = User(
                id=str(uuid.uuid4()),
                name="Franchise Owner",
                email=f"owner-{uuid.uuid4().hex[:8]}@example.com",
                password_hash=get_password_hash("OwnerPass123!"),
                is_active=True,
            )
            db.add(owner)
            await db.flush()
            db.add(
                Franchise(
                    id=franchise_id,
                    user_id=owner.id,
                    franchise_code=f"FC{uuid.uuid4().hex[:6].upper()}",
                    name="Test Franchise",
                    email=f"franchise-{uuid.uuid4().hex[:8]}@example.com",
                    pincode="560001",
                )
            )
            await db.commit()

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": settings.SUPER_ADMIN_EMAIL, "password": settings.SUPER_ADMIN_PASSWORD},
        )
        assert login_resp.status_code == 200
        admin_headers = _auth_headers(login_resp.json()["access_token"])

        approve_resp = await client.post(
            f"/api/v1/int/fleet/drivers/{driver_id}/approve",
            headers=admin_headers,
            json={"franchise_id": franchise_id},
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()
        assert approved["onboarding_status"] == "approved"
        assert approved["status"] == "active"
        assert approved["franchise_id"] == franchise_id


@pytest.mark.asyncio
async def test_bank_before_vehicle_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await _register_driver(client)
        response = await client.post(
            "/api/driver/bank-details",
            headers=_auth_headers(reg["token"]),
            json={
                "accountHolderName": "John Doe",
                "bankName": "Barclays Bank",
                "accountNumber": "12345678",
                "ifscOrRoutingCode": "20-00-00",
            },
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "Vehicle details are required"


@pytest.mark.asyncio
async def test_bank_before_documents_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await _register_driver(client)
        headers = _auth_headers(reg["token"])
        await client.post(
            "/api/driver/vehicle",
            headers=headers,
            json={
                "vehicleType": "Bike",
                "registrationNumber": "AB12 CDE",
                "make": "Honda",
                "model": "CB650R",
                "year": "2023",
                "color": "Red",
            },
        )
        response = await client.post(
            "/api/driver/bank-details",
            headers=headers,
            json={
                "accountHolderName": "John Doe",
                "bankName": "Barclays Bank",
                "accountNumber": "12345678",
                "ifscOrRoutingCode": "20-00-00",
            },
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert "Missing required documents" in body["message"]
