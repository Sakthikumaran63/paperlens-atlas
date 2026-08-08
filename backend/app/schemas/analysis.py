from datetime import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimWithSource(BaseModel):
    claim_id: str
    claim_text: str
    section: str
    page: int

    class Config:
        from_attributes = True


class StructuredPaperSummary(BaseModel):
    executive_summary: str = Field(description="High-level overview of the paper's core findings and value.")
    problem_statement: str = Field(description="Core scientific problem or challenge addressed by the authors.")
    objective: str = Field(description="Primary research objective or aim.")
    methodology_summary: str = Field(description="Summary of proposed method, architecture, or algorithmic approach.")
    key_contributions: List[str] = Field(default_factory=list, description="List of primary technical or theoretical contributions.")
    dataset: str = Field(description="Datasets, benchmark corpora, or experimental data sources utilized.")
    experimental_setup: str = Field(description="Experimental protocols, baselines, metrics, and hardware/software setup.")
    key_results: str = Field(description="Key quantitative or qualitative experimental findings.")
    limitations: str = Field(description="Stated weaknesses, boundary conditions, or failure cases.")
    conclusion: str = Field(description="Final concluding takeaways and summary impact.")

    class Config:
        from_attributes = True


class PaperAnalysisResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    summary: StructuredPaperSummary
    claims: List[ClaimWithSource] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True
