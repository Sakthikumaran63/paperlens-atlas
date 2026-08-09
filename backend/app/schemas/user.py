from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    is_admin: bool = False
    provider: str = "email"
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthLoginRequest(BaseModel):
    provider: str  # "google" or "microsoft"
    email: EmailStr
    name: Optional[str] = None
    provider_id: Optional[str] = None

