# app/routes/cubes.py
from fastapi import APIRouter, HTTPException, Query, Body
from app.db.database import get_db
from bson import ObjectId
from datetime import datetime
from app.schemas.cube import SendFriendRequest, RespondFriendRequest
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter()

@router.get("/dashboard/{user_id}")
async def get_cubes_dashboard(user_id: str):
    db = get_db()

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get incoming friend requests
    requests_cursor = db["friend_requests"].find({"to": ObjectId(user_id)}).sort("requestedAt", -1)

    cube_requests = []
    async for request in requests_cursor:
        from_user = await db["users"].find_one({"_id": request["from"]})
        if from_user:
            mutual_cubes = len(set(from_user.get("friends", [])) & set(user.get("friends", [])))
            cube_requests.append({
                "_id": str(from_user["_id"]),
                "username": from_user["username"],
                "mutualCubes": mutual_cubes,
                "requestedAt": request["requestedAt"]
            })

    total_cubes = len(user.get("friends", []))

    return {
        "totalCubes": total_cubes,
        "cubeRequests": cube_requests
    }


@router.get("/search")
async def search_cubes(query: str = Query(...), user_id: str = Query(...)):
    db = get_db()
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    search_cursor = db["users"].find({"username": {"$regex": query, "$options": "i"}})
    results = []
    async for other_user in search_cursor:
        if str(other_user["_id"]) == user_id:
            continue
        mutual = len(set(other_user.get("friends", [])) & set(user.get("friends", [])))
        results.append({
            "_Id": str(other_user["_id"]),
            "username": other_user["username"],
            "mutualCubes": mutual
        })

    return {"results": results}


@router.post("/request")
async def send_friend_request(payload: SendFriendRequest):
    db = get_db()

    from_user = await db["users"].find_one({"_id": ObjectId(payload.from_user_id)})
    to_user = await db["users"].find_one({"_id": ObjectId(payload.to_user_id)})
    if not from_user or not to_user:
        raise HTTPException(status_code=404, detail="One or both users not found")

    existing = await db["friend_requests"].find_one({"from": ObjectId(payload.from_user_id), "to": ObjectId(payload.to_user_id)})
    if existing:
        raise HTTPException(status_code=400, detail="Request already sent")

    await db["friend_requests"].insert_one({
        "from": ObjectId(payload.from_user_id),
        "to": ObjectId(payload.to_user_id),
        "requestedAt": datetime.utcnow()
    })
    return {"message": "Request sent successfully"}


@router.post("/cancel")
async def cancel_friend_request(payload: SendFriendRequest):
    db = get_db()
    result = await db["friend_requests"].delete_one({
        "from": ObjectId(payload.from_user_id),
        "to": ObjectId(payload.to_user_id)
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Request cancelled"}


@router.post("/respond")
async def respond_to_request(payload: RespondFriendRequest):
    db = get_db()
    request = await db["friend_requests"].find_one({
        "from": ObjectId(payload.from_user_id),
        "to": ObjectId(payload.to_user_id)
    })
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    print(payload.accepted,type(payload.accepted))
    if payload.accepted:
        await db["users"].update_one({"_id": ObjectId(payload.from_user_id)}, {"$addToSet": {"friends": str(payload.to_user_id)}})
        await db["users"].update_one({"_id": ObjectId(payload.to_user_id)}, {"$addToSet": {"friends": str(payload.from_user_id)}})

    await db["friend_requests"].delete_one({
        "from": ObjectId(payload.from_user_id),
        "to": ObjectId(payload.to_user_id)
    })

    return {"message": "Friend request handled"}
