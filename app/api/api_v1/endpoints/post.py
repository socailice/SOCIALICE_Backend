from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from app.schemas.post import PostCreate, UserInfo, CommentInfo, HammerInfo, PostFeedItem, FeedResponse, PostCreateRequest, PostCreateResponse
from app.db.database import get_db
from app.crud.post import insert_post, fetch_feed
from pydantic import BaseModel
from app.schemas.post import CommentInfo, UserInfo

router = APIRouter()

class HammerRequest(BaseModel):
    post_id: str
    username: str
    action: str  # "add" or "remove"

@router.post("/post", response_model=PostCreateResponse)
async def create_post(payload: PostCreateRequest, db=Depends(get_db)):
    post = {
        "userId": payload.userId,
        "mediaUrl": str(payload.mediaUrl),
        "mediaType": payload.mediaType,
        "caption": payload.caption,
        "createdAt": datetime.now(timezone.utc)
    }

    try:
        await db["posts"].insert_one(post)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create post.")

    return PostCreateResponse(
        message="Post created successfully.",
        timestamp=datetime.now(timezone.utc)
    )

@router.get("/posts/paginated")
async def get_today_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        posts_cursor = db["posts"].find({
            "createdAt": {
                "$gte": start_of_day,
                "$lt": end_of_day
            }
        }).sort("createdAt", -1).skip(skip).limit(limit)

        posts = []
        async for post in posts_cursor:
            try:
                u = ObjectId(post["userId"])
            except Exception:
                continue
            user = await db.users.find_one({"_id": u})
            if not user:
                print(f"User not found for post: {post['userId']}")
                continue

            hammer_doc = await db.hammers.find_one({"postId": post["_id"]})
            hammered_by = hammer_doc.get("hammered_by", []) if hammer_doc else []
            hammer_count = len(hammered_by)
            hammered_by_user = False  # Replace with JWT-based logic if needed

            comment_cursor = db.comments.find({"postId": post["_id"]}).sort("createdAt", -1)
            comments = []
            async for comment in comment_cursor:
                comment_user = await db.users.find_one({"_id": comment["userId"]})
                if comment_user:
                    comments.append({
                        "_id": str(comment["_id"]),
                        "text": comment["text"],
                        "userDetails": {
                            "_id": str(comment_user["_id"]),
                            "username": comment_user["username"],
                            "profilePic": comment_user.get("profilePic", "")
                        },
                        "createdAt": comment["createdAt"]
                    })

            posts.append({
                "_id": str(post["_id"]),
                "imageUrl": post["mediaUrl"],
                "caption": post.get("caption", ""),
                "createdAt": post["createdAt"],
                "user": {
                    "_id": str(user["_id"]),
                    "username": user["username"],
                    "profilePic": user.get("profilePic", "")
                },
                "hammers": {
                    "count": hammer_count,
                    "hammeredByCurrentUser": hammered_by_user
                },
                "comments": comments
            })

        return {
            "success": True,
            "message": "Global feed fetched successfully",
            "data": posts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hammer")
async def handle_hammer(data: HammerRequest, db=Depends(get_db)):
    post = await db["posts"].find_one({"_id": ObjectId(data.post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    hammer_doc = await db["hammers"].find_one({"postId": ObjectId(data.post_id)})
    hammered_by = hammer_doc.get("hammered_by", []) if hammer_doc else []

    if data.action == "add":
        if data.username not in hammered_by:
            hammered_by.append(data.username)
    elif data.action == "remove":
        if data.username in hammered_by:
            hammered_by.remove(data.username)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    await db["hammers"].update_one(
        {"postId": ObjectId(data.post_id)},
        {"$set": {"hammered_by": hammered_by,"userId": post["userId"]}},
        upsert=True
    )

    return {
        "message": "Hammer updated successfully",
        "hammers": {
            "count": len(hammered_by),
            "hammeredByCurrentUser": data.username in hammered_by
        }
    }


class CommentRequest(BaseModel):
    post_id: str
    user_id: str
    text: str

@router.post("/comment", response_model=CommentInfo)
async def add_comment(payload: CommentRequest, db=Depends(get_db)):
    # Validate post exists
    post = await db["posts"].find_one({"_id": ObjectId(payload.post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Validate user exists
    user = await db["users"].find_one({"_id": ObjectId(payload.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create comment document
    comment_doc = {
        "postId": ObjectId(payload.post_id),
        "userId": ObjectId(payload.user_id),
        "text": payload.text,
        "createdAt": datetime.now(timezone.utc),
    }

    result = await db["comments"].insert_one(comment_doc)

    return CommentInfo(
        _id=str(result.inserted_id),
        text=payload.text,
        userDetails=UserInfo(
            _id=str(user["_id"]),
            username=user["username"],
            profilePic=user.get("profilePic", "")
        ),
        createdAt=comment_doc["createdAt"]
    )