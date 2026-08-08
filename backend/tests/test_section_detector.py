import tempfile
from pathlib import Path
import fitz
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SectionType
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection
from app.services.section_detector import SectionDetector
from app.utils.storage import get_upload_dir


def test_heading_variation_normalization():
    detector = SectionDetector()

    # Examples requested by user
    sec1, conf1 = detector.classify_heading("Methods")
    assert sec1 == SectionType.METHODOLOGY
    assert conf1 >= 0.95

    sec2, conf2 = detector.classify_heading("Experimental Setup")
    assert sec2 == SectionType.EXPERIMENTS
    assert conf2 >= 0.95

    sec3, conf3 = detector.classify_heading("Data")
    assert sec3 == SectionType.DATASET
    assert conf3 >= 0.90

    sec4, conf4 = detector.classify_heading("Limitations and Future Work")
    assert sec4 == SectionType.LIMITATIONS
    assert conf4 >= 0.95

    # Numbered heading variations
    sec5, conf5 = detector.classify_heading("1. Introduction")
    assert sec5 == SectionType.INTRODUCTION
    assert conf5 >= 0.95

    sec6, conf6 = detector.classify_heading("2. Related Work")
    assert sec6 == SectionType.RELATED_WORK
    assert conf6 >= 0.95

    sec7, conf7 = detector.classify_heading("References")
    assert sec7 == SectionType.REFERENCES
    assert conf7 >= 0.98


def test_section_detector_multipage():
    pages = [
        PaperPage(
            page_number=1,
            raw_text="1. Introduction\n\nThis paper presents research...",
            cleaned_text="1. Introduction\n\nThis paper presents research...",
            character_count=50,
            word_count=10
        ),
        PaperPage(
            page_number=2,
            raw_text="2. Related Work\n\nPrior work in deep learning...\n\n3. Methodology\n\nWe propose...",
            cleaned_text="2. Related Work\n\nPrior work in deep learning...\n\n3. Methodology\n\nWe propose...",
            character_count=100,
            word_count=20
        ),
        PaperPage(
            page_number=3,
            raw_text="4. Experimental Setup\n\nOur experiments run on A100 GPUs...\n\n5. Results\n\nWe achieve 98% accuracy.",
            cleaned_text="4. Experimental Setup\n\nOur experiments run on A100 GPUs...\n\n5. Results\n\nWe achieve 98% accuracy.",
            character_count=100,
            word_count=20
        ),
        PaperPage(
            page_number=4,
            raw_text="6. Limitations and Future Work\n\nOur dataset size is small.\n\n7. References\n\n[1] Vaswani et al.",
            cleaned_text="6. Limitations and Future Work\n\nOur dataset size is small.\n\n7. References\n\n[1] Vaswani et al.",
            character_count=100,
            word_count=20
        )
    ]

    detector = SectionDetector()
    sections = detector.detect_sections(pages)

    assert len(sections) == 7

    # 1. Introduction (page 1 to 2)
    assert sections[0].title == "1. Introduction"
    assert sections[0].section_type == SectionType.INTRODUCTION
    assert sections[0].page_start == 1
    assert sections[0].order_index == 0

    # 2. Related Work (page 2)
    assert sections[1].title == "2. Related Work"
    assert sections[1].section_type == SectionType.RELATED_WORK
    assert sections[1].page_start == 2
    assert sections[1].order_index == 1

    # 3. Methodology (page 2 to 3)
    assert sections[2].title == "3. Methodology"
    assert sections[2].section_type == SectionType.METHODOLOGY
    assert sections[2].page_start == 2
    assert sections[2].order_index == 2

    # 4. Experimental Setup (page 3)
    assert sections[3].title == "4. Experimental Setup"
    assert sections[3].section_type == SectionType.EXPERIMENTS

    # 5. Results (page 3 to 4)
    assert sections[4].title == "5. Results"
    assert sections[4].section_type == SectionType.RESULTS

    # 6. Limitations and Future Work (page 4)
    assert sections[5].title == "6. Limitations and Future Work"
    assert sections[5].section_type == SectionType.LIMITATIONS

    # 7. References (page 4)
    assert sections[6].title == "7. References"
    assert sections[6].section_type == SectionType.REFERENCES
    assert sections[6].page_end == 4


def test_unknown_section_fallback():
    detector = SectionDetector()
    sec_type, conf = detector.classify_heading("Random Custom Section Name")
    assert sec_type == SectionType.OTHER
    assert conf == 0.50


@pytest.mark.asyncio
async def test_paper_processing_section_persistence(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "section_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate a 2-page PDF with clear section headings
    upload_dir = get_upload_dir()
    test_pdf_path = upload_dir / "section_test.pdf"

    doc = fitz.open()
    doc.set_metadata({"title": "Section Detection Test Paper"})

    # Page 1
    p1 = doc.new_page()
    p1.insert_text((50, 50), "1. Introduction\n\nThis paper introduces our model.\n\n2. Methods\n\nWe detail our algorithm.", fontsize=12)

    # Page 2
    p2 = doc.new_page()
    p2.insert_text((50, 50), "3. Experimental Setup\n\nWe benchmark on standard datasets.\n\n4. References\n\n[1] Smith et al.", fontsize=12)

    doc.save(str(test_pdf_path))
    doc.close()

    # Upload
    with open(test_pdf_path, "rb") as f:
        upload_resp = await client.post(
            "/api/v1/papers/upload",
            headers=headers,
            files={"file": ("section_test.pdf", f, "application/pdf")}
        )
    paper_id = upload_resp.json()["paper_id"]

    # Process paper
    proc_resp = await client.post(f"/api/v1/papers/{paper_id}/process", headers=headers)
    assert proc_resp.status_code == 200
    assert proc_resp.json()["status"] == "READY"

    # Query PaperSection DB records
    stmt = select(PaperSection).where(PaperSection.paper_id == paper_id).order_by(PaperSection.order_index)
    res = await db_session.execute(stmt)
    db_sections = res.scalars().all()

    assert len(db_sections) >= 4
    section_types = [s.section_type for s in db_sections]
    assert SectionType.INTRODUCTION in section_types
    assert SectionType.METHODOLOGY in section_types
    assert SectionType.EXPERIMENTS in section_types
    assert SectionType.REFERENCES in section_types

    for s in db_sections:
        assert s.confidence > 0.0
        assert s.normalized_title != ""
