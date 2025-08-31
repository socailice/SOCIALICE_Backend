from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
from app.db.database import get_db
from datetime import datetime, timedelta, timezone
from typing import List
from bson import ObjectId
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse

router = APIRouter()

# In-memory connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            await self.active_connections[username].send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/chat/{username}")
async def chat_websocket(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    db = get_db()
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                sender = data["sender"]
                receiver = data["receiver"]
                content = data["content"]

                # Check if sender and receiver are friends
                sender_user = await db["users"].find_one({"username": sender})
                if not sender_user or receiver not in sender_user.get("friends", []):
                    await websocket.send_json({"error": "Not allowed to chat. Not friends."})
                    continue

                chat_doc = {
                    "sender_username": sender,
                    "receiver_username": receiver,
                    "message": content,
                    "timestamp": datetime.utcnow(),
                    "is_read": False
                }
                result = await db["chats"].insert_one(chat_doc)
                chat_doc["id"] = str(result.inserted_id)

                await manager.send_personal_message({"type": "message", **chat_doc}, receiver)

            elif msg_type == "typing":
                await manager.send_personal_message({"type": "typing", "from": username}, data["receiver"])

            elif msg_type == "stop_typing":
                await manager.send_personal_message({"type": "stop_typing", "from": username}, data["receiver"])

            elif msg_type == "read_receipt":
                message_id = data["message_id"]
                await db["chats"].update_one({"_id": ObjectId(message_id)}, {"$set": {"is_read": True}})
                await manager.send_personal_message({"type": "read_receipt", "message_id": message_id}, data["sender"])

    except WebSocketDisconnect:
        manager.disconnect(username)

@router.post("/send", response_model=ChatMessageResponse)
async def send_message(message: ChatMessageCreate):
    db = get_db()

    sender = await db["users"].find_one({"username": message.sender_username})
    receiver = await db["users"].find_one({"username": message.receiver_username})

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    if str(receiver.get("_id")) not in sender.get("friends", []):
        raise HTTPException(status_code=403, detail="You are not friends with this user")

    chat_doc = {
        "sender_username": message.sender_username,
        "receiver_username": message.receiver_username,
        "message": message.message,
        "timestamp": datetime.utcnow(),
        "is_read": False
    }

    result = await db["chats"].insert_one(chat_doc)
    chat_doc["id"] = str(result.inserted_id)

    return chat_doc

@router.get("/daily", response_model=List[ChatMessageResponse])
async def get_daily_chat(
    sender_username: str = Query(...),
    receiver_username: str = Query(...)
):
    db = get_db()

    # Validate both users exist
    for username in [sender_username, receiver_username]:
        user = await db["users"].find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    now = datetime.now(timezone.utc)  # Use timezone-aware datetime
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    query = {
        "$and": [
            {"$or": [
                {"sender_username": sender_username, "receiver_username": receiver_username},
                {"sender_username": receiver_username, "receiver_username": sender_username}
            ]},
            {"timestamp": {"$gte": start, "$lt": end}}
        ]
    }

    chats = await db["chats"].find(query).sort("timestamp", 1).to_list(length=500)

    for chat in chats:
        chat["id"] = str(chat["_id"])

    return chats

@router.get("/last-messages/{username}")
async def get_last_messages(username: str, limit: int = 20):
    db = get_db()

    # Validate user exists
    current_user = await db["users"].find_one({"username": username})
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch all messages where the user is sender or receiver
    messages_cursor = db["chats"].find({
        "$or": [
            {"sender_username": username},
            {"receiver_username": username}
        ]
    }).sort("timestamp", -1)

    last_messages_map = {}

    async for msg in messages_cursor:
        # Determine the "other" user in the chat
        other_user = msg["receiver_username"] if msg["sender_username"] == username else msg["sender_username"]

        # Only keep the latest message for each conversation
        if other_user not in last_messages_map:
            # Fetch other user details
            user_doc = await db["users"].find_one({"username": other_user})
            if not user_doc:
                continue

            # Count unread messages for this conversation
            unread_count = await db["chats"].count_documents({
                "sender_username": other_user,
                "receiver_username": username,
                "is_read": False
            })

            last_messages_map[other_user] = {
                "userId": str(user_doc["_id"]),
                "username": user_doc["username"],
                "profilePic": user_doc.get("profilePic", ""),
                "lastMessage": msg["message"],
                "timestamp": msg["timestamp"],
                "unreadCount": unread_count
            }

        if len(last_messages_map) >= limit:
            break

    # Sort by most recent timestamp
    sorted_chats = sorted(
        last_messages_map.values(),
        key=lambda x: x["timestamp"],
        reverse=True
    )

    return {
        "success": True,
        "data": sorted_chats
    }
