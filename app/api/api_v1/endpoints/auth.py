from fastapi import APIRouter, HTTPException
from app.schemas.user import User, LoginRequest, UserInDB
from app.db.database import get_db
from app.auth.jwthandler import create_access_token
from datetime import datetime , timedelta , timezone

router = APIRouter()

@router.post("/register")
async def signup(user: User):
    db = get_db()

    # Check if either phone or username already exists
    existing_user = await db["users"].find_one({
        "$or": [
            {"phone": user.phone},
            {"username": user.username}
        ]
    })

    if existing_user:
        if existing_user["phone"] == user.phone:
            raise HTTPException(status_code=400, detail="Phone number already registered")
        else:
            raise HTTPException(status_code=400, detail="Username already taken")

    # Store the user (password is already hashed from frontend)
    user_in_db = UserInDB(
        fullname=user.fullname,
        username=user.username,
        phone=user.phone,
        hashed_password=user.password,
        friends=user.friends
    )

    await db["users"].insert_one(user_in_db.model_dump())
    new_user = await db["users"].find_one({"phone": user.phone})
    return {"message": "User created successfully",
            "user": {
                "_id": str(new_user["_id"]),
                "username": new_user["username"],
                "phone": new_user["phone"]
        }}

@router.post("/login")
async def login(user: LoginRequest):
    db = get_db()

    existing_user = await db["users"].find_one({"username": user.username})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Compare raw hashed password (frontend sends it already hashed)
    if user.password != existing_user["hashed_password"]:
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "_id": str(existing_user["_id"]),
            "username": existing_user["username"],
            "phone": existing_user["phone"]
        }
    }

@router.post("/generate-otp")
async def generate_otp(phone:str):
    db= get_db()

    existing_user = await db["users"].find_one({"phone":phone})
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    elif len(phone)!=10:
        raise HTTPException(status_code=400, detail="Invalid Phone Number")
    
    import random
    otp = random.randint(100000,999999)

    await db["otp"].insert_one(
        {
            "phone":phone,
            "otp":otp,
            "createdAt": datetime.now(timezone.utc) 
         }
    )

    return {"phone":phone,"otp":otp,"message":"OTP generated successfully"}

@router.post("/verify-otp")
async def verify_otp(phone:str, otp:int):
    db=get_db()

    record= await db["otp"].find_one({"phone":phone}, sort=[("createdAt", -1)])
    if not record:
        raise HTTPException(status_code=404, detail="OTP not found. Please generate a new one.")
    
    if (datetime.now(timezone.utc) - record["createdAt"].replace(tzinfo=timezone.utc)) > timedelta(minutes=7):
        await db["otp"].delete_one({"_id": record["_id"]})
        raise HTTPException(status_code=400, detail="OTP expired. Please generate a new one.")
    
    if record["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    await db["otp"].delete_many({"phone": record["phone"]})

    return {"success": True, "message": "OTP verified successfully"}