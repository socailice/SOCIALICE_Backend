from pydantic import BaseModel, EmailStr
from typing import List

class User(BaseModel):
    fullname: str
    username: str
    phone: int
    password: str  # Already hashed from frontend
    friends: List[str] = []

class LoginRequest(BaseModel):
    username: str
    password: str  # Already hashed from frontend

class UserInDB(BaseModel):
    fullname: str
    username: str
    phone: int
    hashed_password: str  # Already hashed from frontend
    friends: List[str] = []
