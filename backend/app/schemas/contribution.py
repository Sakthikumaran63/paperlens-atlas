import uuid
from typing import List
from pydantic import BaseModel, Field
from app.models.enums import ContributionType


class ContributionEvidence(BaseModel):
    page: int
    section: str
    chunk_id: uuid.UUID

    class Config:
        from_attributes = True


class ExtractedContribution(BaseModel):
    text: str = Field(description="Stated or evidence-supported contribution text.")
    contribution_type: ContributionType = Field(
        default=ContributionType.EXPLICIT,
        description="EXPLICIT (explicitly stated by authors) or INFERRED (evidence-supported inferred contribution)."
    )
    evidence: ContributionEvidence

    class Config:
        from_attributes = True


class ContributionExtractionResponse(BaseModel):
    contributions: List[ExtractedContribution] = Field(default_factory=list)

    class Config:
        from_attributes = True
