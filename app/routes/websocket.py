
from fastapi import APIRouter,WebSocket
router=APIRouter()

@router.websocket("/ws/notifications")
async def ws(ws:WebSocket):
    await ws.accept()
    await ws.send_text("connected")
