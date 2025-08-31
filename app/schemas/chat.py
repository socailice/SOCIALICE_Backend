from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class ChatMessageCreate(BaseModel):
    sender_username: str
    receiver_username: str
    message: str


class ChatMessageResponse(BaseModel):
    id: str
    sender_username: str
    receiver_username: str
    message: str
    timestamp: datetime
    is_read: Optional[bool] = False


# New for WebSocket communication
class TypingIndicator(BaseModel):
    type: Literal["typing", "stop_typing"]
    from_user: str
    to_user: str


class ReadReceipt(BaseModel):
    type: Literal["read_receipt"]
    message_id: str
    from_user: str
    to_user: str


# Optional: Unified message model if needed later
class WebSocketEvent(BaseModel):
    type: Literal["message", "typing", "stop_typing", "read_receipt"]
    sender: Optional[str] = None
    receiver: Optional[str] = None
    message: Optional[str] = None
    message_id: Optional[str] = None
