from fastapi import APIRouter, HTTPException, Depends, Query,UploadFile, File, Form
from app.db.database import get_db
from app.schemas.profile import ProfileResponse
from app.schemas.user import UserInDB
from bson import ObjectId
from typing import Optional
from datetime import datetime
import os
from uuid import uuid4
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson.errors import InvalidId

router = APIRouter()

@router.get("/profile/{user_id}")
async def get_profile(user_id: str, current_user_id: Optional[str] = Query(None), db=Depends(get_db)):
    try:
        user_obj_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    posts_cursor = db.posts.find({
        "userId": user_id,
        "createdAt": {"$gte": start_of_day, "$lt": end_of_day}
    })
    posts = [
        {"id": str(post["_id"]), "imageUrl": post.get("mediaUrl"),"time":post.get("createdAt")}
        async for post in posts_cursor
    ]   

    # Default: no current user or same user
    is_socialiced = None

    # Only proceed if a different current_user_id is provided
    if current_user_id and current_user_id != user_id:
        try:
            current_user_obj_id = ObjectId(current_user_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid current user ID format")

        current_user = await db.users.find_one({"_id": current_user_obj_id})
        if not current_user:
            raise HTTPException(status_code=404, detail="Current user not found")

        # Check if already friends
        if user_id in current_user.get("friends", []):
            is_socialiced = True
        else:
            # Check if a friend request exists (pending)
            pending_request = await db.friend_requests.find_one({
                "$or": [
                    {"from": current_user_obj_id, "to": user_obj_id},
                    {"from": user_obj_id, "to": current_user_obj_id}
                ]
            })

            if pending_request:
                is_socialiced = "pending"  # Or use a boolean flag is_pending=True
            else:
                is_socialiced = False

    profile_data = {
        "_Id": str(user["_id"]),
        "username": user["username"],
        "fullname": user["fullname"],
        "profilePic": user.get("profilePic"),
        "isSocialiced": is_socialiced,
        "stats": {
            "socialiced": len(user.get("friends", [])),
            "hammers": await db.posts.count_documents({"user_id": user_id})
        },
        "posts": posts
    }

    return {
        "success": True,
        "message": "Profile fetched successfully",
        "data": profile_data
    }

class ProfilePicUpdate(BaseModel):
    user_id: str
    profilePic: str

@router.put("/profile/update-pic")
async def update_profile_pic(data: ProfilePicUpdate, db=Depends(get_db)):
    try:
        user_id = ObjectId(data.user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"profilePic": data.profilePic}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or already updated")

    return {
        "success": True,
        "message": "Profile picture updated successfully",
        "imageUrl": data.profilePic
    }