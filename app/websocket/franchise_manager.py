from typing import Dict, List
from fastapi import WebSocket


class FranchiseConnectionManager:
    """
    Manages WebSocket connections keyed by franchise_id.
    Allows sending real-time push notifications to a specific franchise.
    """

    def __init__(self):
        # franchise_id -> list of active websocket connections
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, franchise_id: str, websocket: WebSocket):
        if franchise_id not in self.connections:
            self.connections[franchise_id] = []
        self.connections[franchise_id].append(websocket)

    def disconnect(self, franchise_id: str, websocket: WebSocket):
        if franchise_id in self.connections:
            try:
                self.connections[franchise_id].remove(websocket)
            except ValueError:
                pass
            if not self.connections[franchise_id]:
                del self.connections[franchise_id]

    async def send_to_franchise(self, franchise_id: str, data: dict):
        """Send a JSON message to all connections of a specific franchise."""
        if franchise_id not in self.connections:
            return
        disconnected = []
        for ws in self.connections[franchise_id]:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(franchise_id, ws)


franchise_manager = FranchiseConnectionManager()
