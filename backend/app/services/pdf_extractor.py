import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union
import fitz  # PyMuPDF
from pydantic import BaseModel


class PDFExtractionError(Exception):
    """Custom exception raised when PDF text extraction fails."""
    pass


class ExtractedPage(BaseModel):
    page_number: int
    raw_text: str
    cleaned_text: str
    character_count: int
    word_count: int


class ExtractedDocument(BaseModel):
    title_candidate: Optional[str] = None
    author_candidates: Optional[List[str]] = None
    metadata: Dict[str, Any] = {}
    pages: List[ExtractedPage] = []
    page_count: int = 0


class PDFExtractor:
    """
    PyMuPDF-powered PDF text extraction service.
    Extracts structured page content, metadata, title, and author candidates.
    """

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove null bytes and non-printable control characters (except newlines and tabs)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # Normalize multiple spaces per line while preserving double newlines for paragraph breaks
        paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()]
        normalized_paragraphs = [' '.join(p.split()) for p in paragraphs]
        return '\n\n'.join(normalized_paragraphs)

    def detect_title_candidate(self, doc: fitz.Document, pages: List[ExtractedPage]) -> Optional[str]:
        # 1. Check document metadata first
        meta_title = doc.metadata.get("title", "").strip() if doc.metadata else ""
        if meta_title and len(meta_title) > 3 and not meta_title.lower().startswith("untitled"):
            return meta_title

        # 2. Heuristic from first page: first non-empty paragraph
        if pages and pages[0].cleaned_text:
            lines = [line.strip() for line in pages[0].cleaned_text.split('\n\n') if line.strip()]
            if lines:
                candidate = lines[0]
                # Return if candidate length is reasonable for a paper title
                if 5 <= len(candidate) <= 300:
                    return candidate

        return None

    def detect_author_candidates(self, doc: fitz.Document, pages: List[ExtractedPage]) -> Optional[List[str]]:
        # 1. Check document metadata
        meta_author = doc.metadata.get("author", "").strip() if doc.metadata else ""
        if meta_author:
            # Split multiple authors by comma, semicolon, or 'and'
            authors = [a.strip() for a in re.split(r'[,;]|\band\b', meta_author) if a.strip()]
            if authors:
                return authors

        # 2. First page fallback heuristic
        if pages and pages[0].cleaned_text:
            lines = [line.strip() for line in pages[0].cleaned_text.split('\n\n') if line.strip()]
            if len(lines) > 1:
                second_paragraph = lines[1]
                if len(second_paragraph) <= 200 and not second_paragraph.lower().startswith("abstract"):
                    authors = [a.strip() for a in re.split(r'[,;]', second_paragraph) if a.strip()]
                    if authors:
                        return authors

        return None

    def extract(self, pdf_path: Union[str, Path]) -> ExtractedDocument:
        path_obj = Path(pdf_path)
        if not path_obj.exists() or not path_obj.is_file():
            raise PDFExtractionError(f"PDF file does not exist at path: {pdf_path}")

        try:
            doc = fitz.open(str(path_obj))
        except Exception as e:
            raise PDFExtractionError("Failed to open PDF file. The file may be corrupted or encrypted.") from e

        try:
            if doc.is_encrypted:
                # Attempt empty password decryption
                if not doc.authenticate(""):
                    raise PDFExtractionError("PDF file is password protected.")

            extracted_pages: List[ExtractedPage] = []

            for page_index in range(len(doc)):
                page = doc[page_index]
                page_num = page_index + 1  # 1-indexed

                # Extract text with block structure to preserve paragraphs
                blocks = page.get_text("blocks")
                block_texts = []
                for b in blocks:
                    # block format: (x0, y0, x1, y1, "text", block_no, block_type)
                    if b[6] == 0:  # 0 indicates text block
                        text = b[4].strip()
                        if text:
                            block_texts.append(text)

                raw_text = "\n\n".join(block_texts) if block_texts else page.get_text("text")
                raw_text = (raw_text or "").replace("\x00", "")
                cleaned_text = self.clean_text(raw_text).replace("\x00", "")

                char_count = len(cleaned_text)
                word_count = len(cleaned_text.split())

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_num,
                        raw_text=raw_text,
                        cleaned_text=cleaned_text,
                        character_count=char_count,
                        word_count=word_count
                    )
                )

            title_cand = self.detect_title_candidate(doc, extracted_pages)
            if title_cand:
                title_cand = title_cand.replace("\x00", "")
            author_cands = self.detect_author_candidates(doc, extracted_pages)
            if author_cands:
                author_cands = [a.replace("\x00", "") for a in author_cands]

            metadata_dict = {}
            if doc.metadata:
                for k, v in doc.metadata.items():
                    if isinstance(v, str):
                        metadata_dict[k] = v.replace("\x00", "")
                    else:
                        metadata_dict[k] = v

            result = ExtractedDocument(
                title_candidate=title_cand,
                author_candidates=author_cands,
                metadata=metadata_dict,
                pages=extracted_pages,
                page_count=len(extracted_pages)
            )

            doc.close()
            return result

        except Exception as e:
            if 'doc' in locals() and doc:
                doc.close()
            if isinstance(e, PDFExtractionError):
                raise e
            raise PDFExtractionError(f"Error during PDF text extraction: {str(e)}") from e
