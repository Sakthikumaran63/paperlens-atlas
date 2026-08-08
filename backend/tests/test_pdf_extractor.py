import tempfile
from pathlib import Path
import fitz  # PyMuPDF
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus
from app.models.paper import Paper
from app.models.paper_page import PaperPage
from app.services.paper_processing_service import process_paper
from app.services.pdf_extractor import PDFExtractionError, PDFExtractor
from app.utils.storage import get_upload_dir


def create_sample_pdf(file_path: Path, title: str = "Attention Mechanism in Deep Learning", author: str = "Dr. Alice Smith"):
    doc = fitz.open()
    # Metadata
    doc.set_metadata({"title": title, "author": author})

    # Page 1
    page1 = doc.new_page()
    text_p1 = f"{title}\n\n{author}\n\nAbstract\nWe present a novel self-attention mechanism for multi-modal paper comprehension."
    page1.insert_text((50, 50), text_p1, fontsize=12)

    # Page 2
    page2 = doc.new_page()
    text_p2 = "1. Introduction\n\nTransformer architectures have revolutionized natural language processing tasks."
    page2.insert_text((50, 50), text_p2, fontsize=12)

    doc.save(str(file_path))
    doc.close()


def test_pdf_extractor_unit():
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_file = Path(tmp_dir) / "sample_paper.pdf"
        create_sample_pdf(pdf_file)

        extractor = PDFExtractor()
        extracted_doc = extractor.extract(pdf_file)

        assert extracted_doc.page_count == 2
        assert len(extracted_doc.pages) == 2

        # Page 1 checks
        page1 = extracted_doc.pages[0]
        assert page1.page_number == 1
        assert "Attention Mechanism" in page1.cleaned_text
        assert page1.character_count > 0
        assert page1.word_count > 0

        # Page 2 checks
        page2 = extracted_doc.pages[1]
        assert page2.page_number == 2
        assert "Introduction" in page2.cleaned_text
        assert page2.character_count > 0

        # Metadata checks
        assert extracted_doc.title_candidate == "Attention Mechanism in Deep Learning"
        assert extracted_doc.author_candidates == ["Dr. Alice Smith"]


def test_pdf_extractor_invalid_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_pdf = Path(tmp_dir) / "corrupted.pdf"
        with open(fake_pdf, "wb") as f:
            f.write(b"NOT A REAL PDF FILE CONTENT")

        extractor = PDFExtractor()
        with pytest.raises(PDFExtractionError) as exc_info:
            extractor.extract(fake_pdf)

        assert "Failed to open PDF file" in str(exc_info.value)


@pytest.mark.asyncio
async def test_paper_processing_service_pipeline(
    client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Register User & Upload PDF
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "extractor_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create physical test PDF in upload_dir
    upload_dir = get_upload_dir()
    test_pdf_path = upload_dir / "test_extract.pdf"
    create_sample_pdf(test_pdf_path, title="PyMuPDF Paper Processing", author="Bob Author")

    # Upload
    with open(test_pdf_path, "rb") as f:
        upload_resp = await client.post(
            "/api/v1/papers/upload",
            headers=headers,
            files={"file": ("test_extract.pdf", f, "application/pdf")}
        )

    assert upload_resp.status_code == 201
    paper_id = upload_resp.json()["paper_id"]
    assert upload_resp.json()["status"] == "UPLOADED"

    # 2. Trigger processing via endpoint
    proc_resp = await client.post(f"/api/v1/papers/{paper_id}/process", headers=headers)
    assert proc_resp.status_code == 200
    paper_data = proc_resp.json()
    assert paper_data["status"] == "READY"
    assert paper_data["page_count"] == 2
    assert paper_data["processing_error"] is None

    # 3. Verify PaperPage records in database
    stmt = select(PaperPage).where(PaperPage.paper_id == paper_id).order_by(PaperPage.page_number)
    res = await db_session.execute(stmt)
    pages = res.scalars().all()
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[0].raw_text != ""
    assert pages[0].cleaned_text != ""
    assert pages[0].character_count > 0
    assert pages[0].word_count > 0
    assert pages[1].page_number == 2


@pytest.mark.asyncio
async def test_paper_processing_failure_handling(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "failed_proc@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload corrupted PDF content
    corrupted_pdf = b"INVALID_CORRUPTED_PDF_DATA"
    upload_resp = await client.post(
        "/api/v1/papers/upload",
        headers=headers,
        files={"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf), "application/pdf")}
    )
    paper_id = upload_resp.json()["paper_id"]

    # Trigger processing
    proc_resp = await client.post(f"/api/v1/papers/{paper_id}/process", headers=headers)
    assert proc_resp.status_code == 200
    data = proc_resp.json()
    assert data["status"] == "FAILED"
    assert data["processing_error"] is not None
    assert "Failed to open PDF file" in data["processing_error"]
    # Ensure stack traces are not leaked
    assert "Traceback" not in data["processing_error"]
