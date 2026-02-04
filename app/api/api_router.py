# app/api/api_router.py
from fastapi import APIRouter
from app.api.v1 import auth,upload, knowledge_base, website_kb, message,qa
from app.api.v1 import websocket as websocket_router
from app.api.v1 import support as support_router
from app.api.v1 import chat
from app.api.v1 import support_alert

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(upload.router, prefix="/v1/upload", tags=["upload"])
api_router.include_router(knowledge_base.router, prefix="/v1", tags=["knowledge_base"])
api_router.include_router(website_kb.router, prefix="/v1", tags=["website_kb"])
api_router.include_router(message.router, prefix="/v1", tags=["messages"])
api_router.include_router(qa.router, prefix="/v1", tags=["qa"])
api_router.include_router(chat.router, prefix="/v1", tags=["chat"])
api_router.include_router(support_alert.router, prefix="/v1", tags=["support_alert"])
# WebSocket endpoints (no prefix)
api_router.include_router(websocket_router.router)


# Support/admin endpoints
api_router.include_router(support_router.router, prefix="/v1/support", tags=["Support"])