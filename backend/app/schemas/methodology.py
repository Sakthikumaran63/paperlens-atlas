from typing import List, Optional
from pydantic import BaseModel, Field


class MethodologyEvidenceItem(BaseModel):
    evidence_id: str
    section: str
    page: int
    text: str

    class Config:
        from_attributes = True


class MethodologyExtractionResponse(BaseModel):
    approach: Optional[str] = Field(default="Not specified in the paper", description="Overarching research approach or paradigm.")
    model: Optional[str] = Field(default="Not specified in the paper", description="Model architecture, backbone, or neural network structure.")
    algorithms: Optional[str] = Field(default="Not specified in the paper", description="Algorithms, mathematical formulas, or optimization steps.")
    dataset: Optional[str] = Field(default="Not specified in the paper", description="Datasets, benchmark corpora, or data splits utilized.")
    preprocessing: Optional[str] = Field(default="Not specified in the paper", description="Data cleaning, normalization, augmentation, or preprocessing pipeline.")
    training: Optional[str] = Field(default="Not specified in the paper", description="Training procedure, hyperparameters, loss functions, or optimizers.")
    experimental_setup: Optional[str] = Field(default="Not specified in the paper", description="Hardware, software, compute environment, or baselines.")
    metrics: List[str] = Field(default_factory=list, description="Evaluation metrics used to quantify performance.")
    evidence: List[MethodologyEvidenceItem] = Field(default_factory=list, description="Extracted evidence items with source section/page information.")

    class Config:
        from_attributes = True
