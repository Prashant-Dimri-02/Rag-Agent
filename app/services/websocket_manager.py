# app/services/websocket_manager.py
import asyncio
from typing import Dict, Set
from fastapi import WebSocket




class WebSocketManager:
    """Simple in-memory WebSocket manager.


    - users: maps user_id -> WebSocket connection
    - agents: set of WebSocket connections for agents


    NOTE: This in-memory manager works for a single-process deployment. For
    multiple app workers use Redis pub/sub (we can add example later).
    """


    users: Dict[int, WebSocket] = {}
    agents: Set[WebSocket] = set()


    @classmethod
    async def connect_user(cls, user_id: int, ws: WebSocket):
        await ws.accept()
        cls.users[user_id] = ws


    @classmethod
    async def connect_agent(cls, ws: WebSocket):
        await ws.accept()
        cls.agents.add(ws)


    @classmethod
    def disconnect(cls, ws: WebSocket):
        # remove from agents
        cls.agents.discard(ws)
        # remove from users mapping if present
        to_delete = [k for k, v in cls.users.items() if v == ws]
        for k in to_delete:
            del cls.users[k]


    @classmethod
    async def send_to_user(cls, user_id: int, payload: dict):
        ws = cls.users.get(user_id)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception:
                # ignore send errors (connection might be closed)
                cls.disconnect(ws)

    @classmethod
    def broadcast_to_agents(cls, payload: dict):
        # fire-and-forget send to all connected agent websockets
        for ws in list(cls.agents):
            try:
                asyncio.create_task(ws.send_json(payload))
            except Exception:
                cls.disconnect(ws)