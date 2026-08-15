"""
Document Section Detector Module
--------------------------------
Classifies headings and section titles into the 12-class scientific taxonomy.
"""
from typing import List
from app.services.section_detector import DetectedSection, SectionDetector


class DocumentSectionDetector:
    """Detects headings and maps them to scientific section types."""

    def __init__(self, detector: SectionDetector = None):
        self.detector = detector or SectionDetector()

    def detect_sections(self, pages: List[any]) -> List[DetectedSection]:
        return self.detector.detect_sections(pages)
