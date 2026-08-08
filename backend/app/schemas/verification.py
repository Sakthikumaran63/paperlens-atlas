from typing import List
from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    supported: bool
    support_score: float = Field(ge=0.0, le=1.0)
    unsupported_claims: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
