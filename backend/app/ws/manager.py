from __future__ import annotations

from collections import defaultdict
from fastapi import WebSocket


class WSConnectionManager:
    def __init__(self) -> None:
        self._job_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._team_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect_job(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._job_connections[job_id].append(websocket)

    def disconnect_job(self, job_id: str, websocket: WebSocket) -> None:
        if job_id not in self._job_connections:
            return
        try:
            self._job_connections[job_id].remove(websocket)
        except ValueError:
            pass

    async def broadcast_job(self, job_id: str, payload: dict) -> None:
        clients = list(self._job_connections.get(job_id, []))
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                self.disconnect_job(job_id, ws)

    async def connect_team(self, team_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._team_connections[team_id].append(websocket)

    def disconnect_team(self, team_id: str, websocket: WebSocket) -> None:
        if team_id not in self._team_connections:
            return
        try:
            self._team_connections[team_id].remove(websocket)
        except ValueError:
            pass

    async def broadcast_team(self, team_id: str, payload: dict) -> None:
        clients = list(self._team_connections.get(team_id, []))
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                self.disconnect_team(team_id, ws)


ws_manager = WSConnectionManager()
