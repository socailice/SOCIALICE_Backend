from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import List, Optional,Literal
from datetime import datetime

class UserInfo(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    profilePic: HttpUrl

class CommentInfo(BaseModel):
    id: str = Field(..., alias="_id")
    text: str
    userDetails: UserInfo
    createdAt: datetime

class HammerInfo(BaseModel):
    count: int
    hammeredByCurrentUser: bool

# If you're uploading using Form + File, you may not use this directly
class PostCreate(BaseModel):
    userId: str
    caption: str
    # image is usually handled separately via File() in routes

class PostFeedItem(BaseModel):
    id: str = Field(..., alias="_id")
    imageUrl: HttpUrl
    caption: str
    createdAt: datetime
    user: UserInfo
    hammers: HammerInfo
    comments: List[CommentInfo]

class FeedResponse(BaseModel):
    success: bool
    message: str
    data: List[PostFeedItem]

class PostCreateRequest(BaseModel):
    userId: str  # user ID
    mediaUrl: HttpUrl
    mediaType: Literal["image", "video"]
    caption: str

class PostCreateResponse(BaseModel):
    message: str
    timestamp: datetime

class HammerRequest(BaseModel):
    post_id: str
    username: str
    action: str  # "add" or "remove"