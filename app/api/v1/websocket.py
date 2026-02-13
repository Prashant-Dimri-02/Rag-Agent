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

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                message = data.get("message", "").strip()
                if not message:
                    continue

                db = SessionLocal()
                try:
                    # Save user message
                    chat = Chat(
                        sess_id=sess_id,
                        sender="user",
                        message=message
                    )
                    db.add(chat)
                    db.commit()

                    # Check if conversation is assigned
                    session = db.query(ConversationSession)\
                        .filter(ConversationSession.sess_id == sess_id)\
                        .first()

                finally:
                    db.close()

                # ✅ ONLY forward if agent already took over
                if session and session.status == "agent_active":
                    await WebSocketManager.send_to_agent(
                        session.assigned_agent_id,
                        {
                            "type": "user_message",
                            "sess_id": sess_id,
                            "message": message
                        }
                    )

                # ❌ No broadcasting
                # ❌ No sending to unassigned agents

    except WebSocketDisconnect:
        WebSocketManager.disconnect(websocket)


# ==============================
# AGENT WEBSOCKET
# ==============================
@router.websocket("/ws/agent/{agent_id}")
async def agent_ws(websocket: WebSocket, agent_id: int):

    await WebSocketManager.connect_agent(agent_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            typ = data.get("type")

            db = SessionLocal()
            try:

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

                    # Notify user
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

                    # Save agent message (FIXED HERE)
                    chat = Chat(
                        sess_id=sess_id,   # ✅ FIXED
                        sender="agent",
                        message=message
                    )
                    db.add(chat)
                    db.commit()

                    # Send to user
                    await WebSocketManager.send_to_user(
                        sess_id,
                        {
                            "type": "agent_message",
                            "message": message,
                            "agent_id": agent_id
                        }
                    )

            finally:
                db.close()

    except WebSocketDisconnect:
        WebSocketManager.disconnect(websocket)
