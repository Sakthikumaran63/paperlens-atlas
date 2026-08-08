import re
from typing import List, Optional, Tuple
from pydantic import BaseModel

from app.models.enums import SectionType
from app.models.paper_page import PaperPage


class DetectedSection(BaseModel):
    title: str
    normalized_title: str
    section_type: SectionType
    page_start: int
    page_end: int
    order_index: int
    confidence: float


class SectionDetector:
    """
    Deterministic rule-based scientific paper section detector.
    Detects section headings across extracted paper pages, normalizes them into internal section types,
    assigns confidence scores, and tracks page start/end ranges.
    """

    # Mapping of normalized heading keywords to internal SectionType and base confidence score
    TAXONOMY_MAP = {
        # Abstract
        "abstract": (SectionType.ABSTRACT, 0.98),
        
        # Introduction & Background
        "introduction": (SectionType.INTRODUCTION, 0.98),
        "background": (SectionType.INTRODUCTION, 0.95),
        "overview": (SectionType.INTRODUCTION, 0.90),

        # Related Work
        "related work": (SectionType.RELATED_WORK, 0.98),
        "literature review": (SectionType.RELATED_WORK, 0.95),
        "prior work": (SectionType.RELATED_WORK, 0.95),
        "preliminaries": (SectionType.RELATED_WORK, 0.90),

        # Methodology
        "methodology": (SectionType.METHODOLOGY, 0.98),
        "methods": (SectionType.METHODOLOGY, 0.96),
        "materials and methods": (SectionType.METHODOLOGY, 0.98),
        "proposed method": (SectionType.METHODOLOGY, 0.95),
        "proposed methodology": (SectionType.METHODOLOGY, 0.95),
        "approach": (SectionType.METHODOLOGY, 0.92),
        "model architecture": (SectionType.METHODOLOGY, 0.92),
        "system architecture": (SectionType.METHODOLOGY, 0.90),

        # Dataset
        "dataset": (SectionType.DATASET, 0.95),
        "datasets": (SectionType.DATASET, 0.95),
        "data": (SectionType.DATASET, 0.92),
        "datasets and evaluation": (SectionType.DATASET, 0.95),
        "benchmarks": (SectionType.DATASET, 0.90),

        # Experiments
        "experimental setup": (SectionType.EXPERIMENTS, 0.96),
        "experiments": (SectionType.EXPERIMENTS, 0.95),
        "experimental evaluation": (SectionType.EXPERIMENTS, 0.95),
        "implementation details": (SectionType.EXPERIMENTS, 0.92),
        "evaluation": (SectionType.EXPERIMENTS, 0.90),

        # Results
        "results": (SectionType.RESULTS, 0.95),
        "experimental results": (SectionType.RESULTS, 0.95),
        "main results": (SectionType.RESULTS, 0.95),
        "findings": (SectionType.RESULTS, 0.92),

        # Discussion
        "discussion": (SectionType.DISCUSSION, 0.95),
        "analysis": (SectionType.DISCUSSION, 0.92),
        "ablation study": (SectionType.DISCUSSION, 0.95),
        "ablation analysis": (SectionType.DISCUSSION, 0.95),

        # Limitations
        "limitations": (SectionType.LIMITATIONS, 0.95),
        "limitations and future work": (SectionType.LIMITATIONS, 0.95),
        "threats to validity": (SectionType.LIMITATIONS, 0.92),

        # Conclusion
        "conclusion": (SectionType.CONCLUSION, 0.95),
        "conclusions": (SectionType.CONCLUSION, 0.95),
        "conclusion and future work": (SectionType.CONCLUSION, 0.95),
        "concluding remarks": (SectionType.CONCLUSION, 0.92),
        "summary": (SectionType.CONCLUSION, 0.90),

        # References
        "references": (SectionType.REFERENCES, 0.98),
        "bibliography": (SectionType.REFERENCES, 0.98),
    }

    # Regex patterns for detecting heading lines
    NUMBERED_HEADING_REGEX = re.compile(
        r'^(?:(?:\d+\.)+\d*|\b[IVXLCDM]+\.|\b\d+\b)\s+([A-Z][A-Za-z0-9\s\-\,\:\&]{2,80})$'
    )
    UNNUMBERED_HEADING_REGEX = re.compile(
        r'^(Abstract|Introduction|Background|Related Work|Literature Review|Methodology|Methods|Materials and Methods|Proposed Method|Experimental Setup|Experiments|Results|Discussion|Limitations|Limitations and Future Work|Conclusion|Conclusions|References|Bibliography)$',
        re.IGNORECASE
    )

    def normalize_title(self, raw_title: str) -> str:
        # Strip numbering, section markers, punctuation, and lowercase
        cleaned = re.sub(r'^(?:(?:\d+\.)+\d*|\b[IVXLCDM]+\.|\b\d+\b)\s*', '', raw_title.strip())
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        return ' '.join(cleaned.lower().split())

    def classify_heading(self, raw_title: str) -> Tuple[SectionType, float]:
        norm_title = self.normalize_title(raw_title)
        
        # 1. Exact taxonomy map lookup
        if norm_title in self.TAXONOMY_MAP:
            sec_type, confidence = self.TAXONOMY_MAP[norm_title]
            return sec_type, confidence

        # 2. Substring or keyword lookup
        for key, (sec_type, base_conf) in self.TAXONOMY_MAP.items():
            if key in norm_title or norm_title in key:
                return sec_type, max(0.85, base_conf - 0.05)

        # 3. Fallback for unknown sections
        return SectionType.OTHER, 0.50

    def detect_sections(self, pages: List[PaperPage]) -> List[DetectedSection]:
        if not pages:
            return []

        raw_candidates = []

        for page in pages:
            text = page.cleaned_text or page.raw_text or ""
            if not text:
                continue

            # Split text by paragraph or newline
            lines = [line.strip() for line in text.split('\n\n') if line.strip()]
            for line in lines:
                # Check single line candidates
                first_line = line.split('\n')[0].strip()
                if len(first_line) > 100:
                    continue

                # Match regex
                is_heading = False
                if self.UNNUMBERED_HEADING_REGEX.match(first_line):
                    is_heading = True
                elif self.NUMBERED_HEADING_REGEX.match(first_line):
                    is_heading = True
                elif first_line.isupper() and 3 <= len(first_line) <= 60:
                    is_heading = True

                if is_heading:
                    raw_candidates.append((first_line, page.page_number))

        if not raw_candidates:
            # Fallback: create a single OTHER section spanning all pages
            return [
                DetectedSection(
                    title="Full Document",
                    normalized_title="full document",
                    section_type=SectionType.OTHER,
                    page_start=pages[0].page_number,
                    page_end=pages[-1].page_number,
                    order_index=0,
                    confidence=0.50
                )
            ]

        detected_sections: List[DetectedSection] = []
        for idx, (raw_title, page_num) in enumerate(raw_candidates):
            norm_title = self.normalize_title(raw_title)
            sec_type, conf = self.classify_heading(raw_title)

            detected_sections.append(
                DetectedSection(
                    title=raw_title,
                    normalized_title=norm_title or raw_title.lower(),
                    section_type=sec_type,
                    page_start=page_num,
                    page_end=page_num,  # Will be updated in post-processing
                    order_index=idx,
                    confidence=conf
                )
            )

        # Post-process page_end ranges
        total_pages = pages[-1].page_number
        for i in range(len(detected_sections)):
            if i < len(detected_sections) - 1:
                next_start = detected_sections[i + 1].page_start
                detected_sections[i].page_end = max(detected_sections[i].page_start, next_start)
            else:
                detected_sections[i].page_end = total_pages

        return detected_sections
