from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.websocket.franchise_manager import franchise_manager

router = APIRouter(prefix="/ws", tags=["WebSocket - Trip Sheet Notifications"])


@router.websocket("/trip-sheet-notifications")
async def trip_sheet_notification_socket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for franchise trip sheet notifications.

    Connect with a valid JWT token as a query param:
        ws://host/ws/trip-sheet-notifications?token=<jwt>

    When a trip sheet is created and your franchise is set as the
    destination, you will receive a real-time JSON notification:
    {
        "event": "new_incoming_trip_sheet",
        "trip_sheet_id": "...",
        "from_franchise": "...",
        "total_packages": 10,
        "total_freight": 500.0
    }
    """
    from app.utils.jwt import verify_access_token
    from app.models.user import User
    from app.models.franchise import Franchise

    # Accept the connection first so we can close it with a standard WebSocket code if needed
    await websocket.accept()

    # Authenticate the user from the token query param
    try:
        payload = verify_access_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Resolve the franchise_id for this user
    franchise_id = None
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            await websocket.close(code=4003, reason="User not found")
            return

        franchise = (await db.execute(
            select(Franchise).where(Franchise.user_id == user_id)
        )).scalar_one_or_none()

        if franchise:
            franchise_id = franchise.id

    if not franchise_id:
        # Non-franchise users (e.g. super admin) still connect but won't receive targeted messages
        # Connect them with their user_id as key for future use
        franchise_id = f"user:{user_id}"

    await franchise_manager.connect(franchise_id, websocket)

    try:
        while True:
            # Keep connection alive; we only push messages to the client
            await websocket.receive_text()
    except WebSocketDisconnect:
        franchise_manager.disconnect(franchise_id, websocket)
