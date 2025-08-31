from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import List
from bson import ObjectId

from app.schemas.post import PostCreate, PostFeedItem, UserInfo, CommentInfo, HammerInfo

async def insert_post(db: AsyncIOMotorDatabase, post: PostCreate, image_url: str = None) -> PostFeedItem:
    data = {
        "user_id": ObjectId(post.user_id),
        "caption": post.caption,
        "imageUrl": image_url,
        "createdAt": datetime.utcnow()
    }
    result = await db.posts.insert_one(data)
    data["_id"] = str(result.inserted_id)
    # Initialize nested fields
    return PostFeedItem(
        _id=data["_id"],
        imageUrl=data["imageUrl"],
        caption=data["caption"],
        createdAt=data["createdAt"],
        user=UserInfo(_id=post.user_id, username="unknown", profilePic=""),
        hammers=HammerInfo(count=0, hammeredByCurrentUser=False),
        comments=[]
    )

async def fetch_feed(db: AsyncIOMotorDatabase, page: int, size: int) -> List[PostFeedItem]:
    cursor = db.posts.aggregate([
        {"$sort": {"createdAt": -1}},
        {"$skip": (page - 1) * size},
        {"$limit": size},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$lookup": {"from": "comments", "localField": "_id", "foreignField": "post_id", "as": "comments"}},
        {"$lookup": {"from": "hammers_meta", "localField": "_id", "foreignField": "post_id", "as": "hammersArr"}},
        {"$addFields": {"hammers": {"$arrayElemAt": ["$hammersArr", 0]}}},
        {"$project": {"hammersArr": 0, "user.password": 0}}
    ])
    items = []
    async for doc in cursor:
        items.append(PostFeedItem(
            _id=str(doc["_id"]),
            imageUrl=doc["imageUrl"],
            caption=doc["caption"],
            createdAt=doc["createdAt"],
            user=UserInfo(
                _id=str(doc["user"]["_id"]),
                username=doc["user"]["username"],
                profilePic=doc["user"]["profilePic"]
            ),
            hammers=HammerInfo(
                count=doc["hammers"]["count"] if doc.get("hammers") else 0,
                hammeredByCurrentUser=doc.get("hammers", {}).get("hammeredByCurrentUser", False)
            ),
            comments=[
                CommentInfo(
                    _id=str(c["_id"]),
                    text=c["text"],
                    userDetails=UserInfo(
                        _id=str(c["userDetails"]["_id"]),
                        username=c["userDetails"]["username"],
                        profilePic=c["userDetails"]["profilePic"]
                    ),
                    createdAt=c["createdAt"]
                ) for c in doc.get("comments", [])
            ]
        ))
    return items