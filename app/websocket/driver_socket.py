from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.websocket.driver_manager import driver_manager

router = APIRouter(prefix="/ws", tags=["WebSocket - Driver"])


@router.websocket("/driver")
async def driver_notification_socket(websocket: WebSocket, token: str = Query(...)):
    from app.utils.jwt import verify_access_token
    from app.models.user import User
    from app.modules.fleet.models.driver import Driver
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    import uuid
    from datetime import datetime
    from app.modules.fleet.models.driver_location import DriverLocation
    from sqlalchemy.dialects.mysql import insert
    from app.websocket.franchise_manager import franchise_manager

    await websocket.accept()
    payload = verify_access_token(token)
    if not payload or payload.get("role") != "driver":
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    driver_id = payload.get("driver_id")
    franchise_id = None
    
    async with AsyncSessionLocal() as db:
        if not driver_id:
            user_id = payload.get("user_id")
            driver = (
                await db.execute(select(Driver).where(Driver.user_id == user_id, Driver.deleted_at.is_(None)))
            ).scalar_one_or_none()
            if not driver:
                await websocket.close(code=4003, reason="Driver not found")
                return
            driver_id = driver.id
            franchise_id = driver.franchise_id
        else:
            driver = (
                await db.execute(select(Driver).where(Driver.id == driver_id, Driver.deleted_at.is_(None)))
            ).scalar_one_or_none()
            if driver:
                franchise_id = driver.franchise_id

    await driver_manager.connect(driver_id, websocket)
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("event") == "LOCATION_SYNC":
                lat = msg.get("lat")
                lng = msg.get("lng")
                if lat is not None and lng is not None:
                    async with AsyncSessionLocal() as db:
                        stmt = insert(DriverLocation).values(
                            id=str(uuid.uuid4()),
                            driver_id=driver_id,
                            latitude=float(lat),
                            longitude=float(lng),
                            speed=msg.get("speed"),
                            heading=msg.get("heading"),
                            accuracy=msg.get("accuracy"),
                            updated_at=datetime.utcnow()
                        )
                        stmt = stmt.on_duplicate_key_update(
                            latitude=stmt.inserted.latitude,
                            longitude=stmt.inserted.longitude,
                            speed=stmt.inserted.speed,
                            heading=stmt.inserted.heading,
                            accuracy=stmt.inserted.accuracy,
                            updated_at=stmt.inserted.updated_at
                        )
                        await db.execute(stmt)
                        await db.commit()
                    
                    if franchise_id:
                        await franchise_manager.send_to_franchise(
                            franchise_id, 
                            {
                                "event": "DRIVER_LOCATION_UPDATE",
                                "driver_id": driver_id,
                                "lat": lat,
                                "lng": lng,
                                "speed": msg.get("speed"),
                                "heading": msg.get("heading")
                            }
                        )
    except WebSocketDisconnect:
        driver_manager.disconnect(driver_id, websocket)
