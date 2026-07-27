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

    await websocket.accept()
    payload = verify_access_token(token)
    if not payload or payload.get("role") != "driver":
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    driver_id = payload.get("driver_id")
    if not driver_id:
        async with AsyncSessionLocal() as db:
            user_id = payload.get("user_id")
            driver = (
                await db.execute(select(Driver).where(Driver.user_id == user_id, Driver.deleted_at.is_(None)))
            ).scalar_one_or_none()
            if not driver:
                await websocket.close(code=4003, reason="Driver not found")
                return
            driver_id = driver.id

    await driver_manager.connect(driver_id, websocket)
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("event") == "LOCATION_SYNC":
                pass
    except WebSocketDisconnect:
        driver_manager.disconnect(driver_id, websocket)
