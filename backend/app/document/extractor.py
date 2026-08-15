"""
Document PDF Extraction Module
------------------------------
Extracts text, page counts, and structural metadata using PyMuPDF while preserving page boundaries.
"""
from pathlib import Path
from typing import List, Union
from app.services.pdf_extractor import ExtractedDocument, PDFExtractor


class DocumentExtractor:
    """Extracts raw and cleaned text from PDF files preserving page structure."""

    def __init__(self, extractor: PDFExtractor = None):
        self.extractor = extractor or PDFExtractor()

    def extract(self, file_path: Union[str, Path]) -> ExtractedDocument:
        return self.extractor.extract(file_path)
