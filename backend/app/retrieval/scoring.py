"""
Retrieval Scoring Formulas
---------------------------
Calculates composite hybrid scores using configurable weights:
final_score = (semantic * w_sem) + (section * w_sec) + (bm25 * w_bm25)
"""
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class ScoringWeights:
    semantic: float = 0.60
    section: float = 0.25
    bm25: float = 0.15


class HybridScorer:
    """Computes final hybrid retrieval scores."""

    def __init__(self, weights: ScoringWeights = None):
        self.weights = weights or ScoringWeights(
            semantic=getattr(settings, "RETRIEVAL_SEMANTIC_WEIGHT", 0.60),
            section=getattr(settings, "RETRIEVAL_SECTION_WEIGHT", 0.25),
            bm25=getattr(settings, "RETRIEVAL_KEYWORD_WEIGHT", 0.15),
        )

    def calculate_final_score(
        self,
        semantic_score: float,
        section_score: float,
        bm25_score: float,
    ) -> float:
        score = (
            (semantic_score * self.weights.semantic)
            + (section_score * self.weights.section)
            + (bm25_score * self.weights.bm25)
        )
        return round(float(score), 4)
