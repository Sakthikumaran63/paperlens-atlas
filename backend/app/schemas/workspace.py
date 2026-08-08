from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
