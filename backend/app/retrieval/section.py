"""
Section Taxonomy Routing Module
--------------------------------
Calculates section alignment boost scores based on question intent priorities.
"""
from typing import List
from app.models.enums import SectionType


class SectionRouter:
    """Calculates section score based on intent priority matching."""

    @staticmethod
    def calculate_section_score(chunk_sec_type: SectionType, priorities: List[SectionType]) -> float:
        if not priorities:
            return 0.5

        if chunk_sec_type in priorities:
            rank_idx = priorities.index(chunk_sec_type)
            if rank_idx == 0:
                return 1.0
            elif rank_idx == 1:
                return 0.8
            else:
                return 0.6

        # Abstract / conclusion general fallback
        if chunk_sec_type in [SectionType.ABSTRACT, SectionType.CONCLUSION]:
            return 0.4

        return 0.1
