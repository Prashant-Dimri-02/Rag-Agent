# app/api/v1/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import WebSocketManager
from app.db.session import SessionLocal
from app.models.chat import Chat
from app.models.session import ConversationSession

router = APIRouter()


# ==============================
# USER WEBSOCKET
# ==============================

@router.websocket("/ws/user/{sess_id}")
async def user_ws(websocket: WebSocket, sess_id: int):

    await WebSocketManager.connect_user(sess_id, websocket)

    db = SessionLocal()  # ✅ Create ONE session per WebSocket

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                message = data.get("message", "").strip()
                if not message:
                    continue

                # Save user message
                chat = Chat(
                    sess_id=sess_id,
                    sender="user",
                    message=message
                )
                db.add(chat)
                db.commit()

                # Check if conversation assigned
                session = (
                    db.query(ConversationSession)
                    .filter(ConversationSession.sess_id == sess_id)
                    .first()
                )

                # Forward only if agent active
                if session and session.status == "agent_active":
                    await WebSocketManager.send_to_agent(
                        session.assigned_agent_id,
                        {
                            "type": "user_message",
                            "sess_id": sess_id,
                            "message": message
                        }
                    )

    except WebSocketDisconnect:
        pass
    finally:
        db.close()  # ✅ Close when socket disconnects
        WebSocketManager.disconnect(websocket)


# ==============================
# AGENT WEBSOCKET
# ==============================

@router.websocket("/ws/agent/{agent_id}")
async def agent_ws(websocket: WebSocket, agent_id: int):

    await WebSocketManager.connect_agent(agent_id, websocket)

    db = SessionLocal()  # ✅ Create ONE session per WebSocket

    try:
        while True:
            data = await websocket.receive_json()
            typ = data.get("type")

            # ========================
            # TAKEOVER
            # ========================
            if typ == "takeover":

                sess_id = data.get("sess_id")

                session = (
                    db.query(ConversationSession)
                    .filter(ConversationSession.sess_id == sess_id)
                    .with_for_update()
                    .first()
                )

                if not session:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Session not found"
                    })
                    continue

                if session.assigned_agent_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Already assigned to another agent"
                    })
                    continue

                session.status = "agent_active"
                session.assigned_agent_id = agent_id
                db.commit()

                await websocket.send_json({
                    "type": "ok",
                    "action": "taken_over",
                    "sess_id": sess_id
                })

                await WebSocketManager.send_to_user(
                    sess_id,
                    {
                        "type": "agent_joined",
                        "agent_id": agent_id,
                        "message": "A support agent has joined the chat."
                    }
                )

            # ========================
            # AGENT REPLY
            # ========================
            elif typ == "reply":

                sess_id = data.get("sess_id")
                message = data.get("message", "").strip()

                if not message:
                    continue

                session = (
                    db.query(ConversationSession)
                    .filter(ConversationSession.sess_id == sess_id)
                    .first()
                )

                if not session or session.assigned_agent_id != agent_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not authorized for this conversation"
                    })
                    continue

                chat = Chat(
                    sess_id=sess_id,
                    sender="agent",
                    message=message
                )
                db.add(chat)
                db.commit()

                await WebSocketManager.send_to_user(
                    sess_id,
                    {
                        "type": "agent_message",
                        "message": message,
                        "agent_id": agent_id
                    }
                )

    except WebSocketDisconnect:
        pass
    finally:
        db.close()  # ✅ Close once when socket closes
        WebSocketManager.disconnect(websocket)
