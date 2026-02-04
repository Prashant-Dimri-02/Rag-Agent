# app/services/websocket_manager.py

from typing import Dict
from fastapi import WebSocket


class WebSocketManager:
    """
    In-memory WebSocket connection manager.

    users  -> user_id   : WebSocket
    agents -> agent_id  : WebSocket

    NOTE:
    This works only for single-process deployments.
    For multi-worker production use Redis pub/sub.
    """

    users: Dict[int, WebSocket] = {}
    agents: Dict[int, WebSocket] = {}

    # ===============================
    # CONNECT METHODS
    # ===============================

    @classmethod
    async def connect_user(cls, user_id: int, ws: WebSocket):
        await ws.accept()

        # If user reconnects → replace old socket
        if user_id in cls.users:
            try:
                await cls.users[user_id].close()
            except:
                pass

        cls.users[user_id] = ws

    @classmethod
    async def connect_agent(cls, agent_id: int, ws: WebSocket):
        await ws.accept()

        # Replace old connection if reconnecting
        if agent_id in cls.agents:
            try:
                await cls.agents[agent_id].close()
            except:
                pass

        cls.agents[agent_id] = ws

    # ===============================
    # DISCONNECT
    # ===============================

    @classmethod
    def disconnect(cls, ws: WebSocket):

        # Remove from users
        for user_id, socket in list(cls.users.items()):
            if socket == ws:
                del cls.users[user_id]

        # Remove from agents
        for agent_id, socket in list(cls.agents.items()):
            if socket == ws:
                del cls.agents[agent_id]

    # ===============================
    # SEND METHODS
    # ===============================

    @classmethod
    async def send_to_user(cls, user_id: int, payload: dict):
        ws = cls.users.get(user_id)

        if not ws:
            return

        try:
            await ws.send_json(payload)
        except Exception:
            cls.disconnect(ws)

    @classmethod
    async def send_to_agent(cls, agent_id: int, payload: dict):
        print("Trying to send to agent:", agent_id)
        print("Connected agents:", cls.agents.keys())

        ws = cls.agents.get(agent_id)

        if not ws:
            print("Agent not connected")
            return

        try:
            await ws.send_json(payload)
        except Exception:
            cls.disconnect(ws)

    @classmethod
    async def broadcast_to_agents(cls, payload: dict):
        """
        Send message to ALL connected agents.
        Used for new chat alerts.
        """
        for agent_id, ws in list(cls.agents.items()):
            try:
                await ws.send_json(payload)
            except Exception:
                cls.disconnect(ws)

    # ===============================
    # OPTIONAL HELPERS
    # ===============================

    @classmethod
    def is_user_online(cls, user_id: int) -> bool:
        return user_id in cls.users

    @classmethod
    def is_agent_online(cls, agent_id: int) -> bool:
        return agent_id in cls.agents

    @classmethod
    def connected_agents_count(cls) -> int:
        return len(cls.agents)

    @classmethod
    def connected_users_count(cls) -> int:
        return len(cls.users)
