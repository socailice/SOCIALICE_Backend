from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CubeRequestItem(BaseModel):
    _id: str  # sender user ID
    username: str
    mutualCubes: int
    requestedAt: datetime


class CubeDashboardResponse(BaseModel):
    totalCubes: int
    cubeRequests: List[CubeRequestItem]


class CubeSearchResult(BaseModel):
    _Id: str
    username: str
    mutualCubes: int


class CubeSearchResponse(BaseModel):
    results: List[CubeSearchResult]


class SendFriendRequest(BaseModel):
    from_user_id: str
    to_user_id: str


class RespondFriendRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    accepted: bool  # True = Accept, False = Decline
