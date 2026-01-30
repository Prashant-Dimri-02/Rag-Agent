# app/api/v1/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import WebSocketManager
from app.db.session import SessionLocal
from app.models.chat import Chat


router = APIRouter()




@router.websocket("/ws/user/{user_id}")
async def user_ws(websocket: WebSocket, user_id: int):
    # For websocket connections we create a DB session only if we need it.
    await WebSocketManager.connect_user(user_id, websocket)
    try:
        while True:
            # expecting client sends keep-alive or messages
            data = await websocket.receive_json()
            # data example: {"type":"message","message":"hi"}
            if data.get("type") == "message":
            # save the incoming user message into DB
                db = SessionLocal()
                try:
                    chat = Chat(user_id=user_id, sender="user", message=data.get("message", ""))
                    db.add(chat)
                    db.commit()
                    db.refresh(chat)
                finally:
                    db.close()

                # optionally, you may call the QAService here to get a bot reply
                # but to keep separation of concerns we recommend HTTP POST to QA endpoint
    except WebSocketDisconnect:
        WebSocketManager.disconnect(websocket)




@router.websocket("/ws/agent")
async def agent_ws(websocket: WebSocket):
    await WebSocketManager.connect_agent(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # agent messages should follow a schema, for example:
            # {"type":"takeover","user_id":123,"agent_id":5}
            # {"type":"reply","user_id":123,"agent_id":5,"message":"hello"}

            typ = data.get("type")
            if typ == "takeover":
                user_id = data.get("user_id")
                agent_id = data.get("agent_id")
                # send a simple confirmation to this agent (fire-and-forget)
                await websocket.send_json({"type": "ok", "action": "taken_over", "user_id": user_id})
            elif typ == "reply":
                user_id = data.get("user_id")
                message = data.get("message")
                # persist reply and forward to user
                db = SessionLocal()
                try:
                    chat = Chat(user_id=user_id, sender="agent", message=message, taken_over=True)
                    db.add(chat)
                    db.commit()
                finally:
                    db.close()
                await WebSocketManager.send_to_user(user_id, {"type": "agent_message", "message": message})


    except WebSocketDisconnect:
        WebSocketManager.disconnect(websocket)