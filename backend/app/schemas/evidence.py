import uuid
from typing import List
from pydantic import BaseModel


class SelectedEvidenceItem(BaseModel):
    evidence_id: str
    chunk_id: uuid.UUID
    page: int
    section: str
    text: str
    retrieval_score: float

    class Config:
        from_attributes = True


class EvidencePackage(BaseModel):
    items: List[SelectedEvidenceItem]
    total_tokens: int
    total_items: int
    package_hash: str

    class Config:
        from_attributes = True
