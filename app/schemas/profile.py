# app/schemas/profile.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class ProfilePostItem(BaseModel):
    id: str
    imageUrl: HttpUrl

class Stats(BaseModel):
    socialiced: int
    hammers: int

class ProfileResponseData(BaseModel):
    _Id: str
    username: str
    fullname: str
    profilePic: HttpUrl
    isSocialiced: Optional[bool]  # null, true, or false
    stats: Stats
    posts: List[ProfilePostItem]

class ProfileResponse(BaseModel):
    success: bool
    message: str
    data: ProfileResponseData
