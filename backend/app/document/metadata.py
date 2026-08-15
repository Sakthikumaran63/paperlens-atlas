"""
Document Metadata Extraction Module
-----------------------------------
Extracts paper title, authors, DOI, and page counts from header blocks.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PaperMetadata:
    title: Optional[str] = None
    authors: Optional[str] = None
    doi: Optional[str] = None
    page_count: int = 0
    abstract: Optional[str] = None
