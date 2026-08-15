"""
Document Sanitization & Prompt Injection Defense Module
-------------------------------------------------------
Encapsulates untrusted paper content within XML tags and sanitizes control characters.
"""
import re


class DocumentSanitizer:
    """Sanitizes text and wraps untrusted content in AI safety containers."""

    @staticmethod
    def sanitize_text(text: str) -> str:
        if not text:
            return ""
        # Strip null bytes and control chars
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    @staticmethod
    def wrap_untrusted_content(content: str) -> str:
        sanitized = DocumentSanitizer.sanitize_text(content)
        return f"<UNTRUSTED_DOCUMENT_CONTENT>\n{sanitized}\n</UNTRUSTED_DOCUMENT_CONTENT>"
