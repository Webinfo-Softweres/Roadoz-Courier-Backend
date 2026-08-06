from typing import Dict, List

from fastapi import WebSocket


class DriverConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, driver_id: str, websocket: WebSocket):
        if driver_id not in self.connections:
            self.connections[driver_id] = []
        self.connections[driver_id].append(websocket)

    def disconnect(self, driver_id: str, websocket: WebSocket):
        if driver_id not in self.connections:
            return
        try:
            self.connections[driver_id].remove(websocket)
        except ValueError:
            pass
        if not self.connections[driver_id]:
            del self.connections[driver_id]

    async def send_to_driver(self, driver_id: str, data: dict):
        if driver_id not in self.connections:
            return
        dead = []
        for ws in self.connections[driver_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(driver_id, ws)


driver_manager = DriverConnectionManager()
