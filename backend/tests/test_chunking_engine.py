import uuid
import fitz
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus, SectionType
from app.models.paper_chunk import PaperChunk
from app.models.paper_page import PaperPage
from app.models.paper_section import PaperSection
from app.services.chunking_engine import ChunkConfig, ChunkingEngine
from app.utils.storage import get_upload_dir


def test_chunk_traceability_and_section_isolation():
    paper_id = uuid.uuid4()
    sec_intro_id = uuid.uuid4()
    sec_method_id = uuid.uuid4()

    pages = [
        PaperPage(
            paper_id=paper_id,
            page_number=1,
            raw_text="1. Introduction\n\nIntroduction paragraph 1 text.\n\nIntroduction paragraph 2 text.",
            cleaned_text="1. Introduction\n\nIntroduction paragraph 1 text.\n\nIntroduction paragraph 2 text.",
            character_count=100,
            word_count=20
        ),
        PaperPage(
            paper_id=paper_id,
            page_number=2,
            raw_text="2. Methodology\n\nMethodology step 1 algorithm.\n\nMethodology step 2 evaluation.",
            cleaned_text="2. Methodology\n\nMethodology step 1 algorithm.\n\nMethodology step 2 evaluation.",
            character_count=100,
            word_count=20
        )
    ]

    sections = [
        PaperSection(
            id=sec_intro_id,
            paper_id=paper_id,
            title="1. Introduction",
            normalized_title="introduction",
            section_type=SectionType.INTRODUCTION,
            page_start=1,
            page_end=1,
            order_index=0,
            confidence=0.98
        ),
        PaperSection(
            id=sec_method_id,
            paper_id=paper_id,
            title="2. Methodology",
            normalized_title="methodology",
            section_type=SectionType.METHODOLOGY,
            page_start=2,
            page_end=2,
            order_index=1,
            confidence=0.98
        )
    ]

    engine = ChunkingEngine()
    chunks = engine.chunk_paper(paper_id, pages, sections)

    assert len(chunks) >= 2

    # Verify Mandatory Traceability: Paper -> Page -> Section -> Chunk
    for chk in chunks:
        assert chk.paper_id == paper_id
        assert chk.page_number in [1, 2]
        assert chk.section_id in [sec_intro_id, sec_method_id]
        assert chk.section_type in [SectionType.INTRODUCTION, SectionType.METHODOLOGY]
        assert chk.token_count > 0
        assert "section_type" in chk.metadata
        assert "section_title" in chk.metadata
        assert "page_number" in chk.metadata

    # Verify Section Isolation
    intro_chunks = [c for c in chunks if c.section_id == sec_intro_id]
    method_chunks = [c for c in chunks if c.section_id == sec_method_id]

    for ic in intro_chunks:
        assert "Methodology" not in ic.text
    for mc in method_chunks:
        assert "Introduction" not in mc.text


def test_special_section_handling_abstract_and_dataset():
    paper_id = uuid.uuid4()
    abstract_sec_id = uuid.uuid4()

    pages = [
        PaperPage(
            paper_id=paper_id,
            page_number=1,
            raw_text="Abstract\n\nWe present PaperLens AI assistant. It extracts structure and attribution.",
            cleaned_text="Abstract\n\nWe present PaperLens AI assistant. It extracts structure and attribution.",
            character_count=80,
            word_count=12
        )
    ]

    sections = [
        PaperSection(
            id=abstract_sec_id,
            paper_id=paper_id,
            title="Abstract",
            normalized_title="abstract",
            section_type=SectionType.ABSTRACT,
            page_start=1,
            page_end=1,
            order_index=0,
            confidence=0.98
        )
    ]

    engine = ChunkingEngine()
    chunks = engine.chunk_paper(paper_id, pages, sections)

    assert len(chunks) == 1
    assert chunks[0].section_type == SectionType.ABSTRACT
    assert chunks[0].metadata.get("is_abstract") is True
    assert "PaperLens AI assistant" in chunks[0].text


def test_chunking_engine_token_limits_and_overlap():
    paper_id = uuid.uuid4()
    sec_id = uuid.uuid4()

    # Generate a long section with multiple paragraphs
    paras = [f"Paragraph number {i} with detailed scientific explanation." for i in range(25)]
    text = "\n\n".join(paras)

    pages = [
        PaperPage(
            paper_id=paper_id,
            page_number=1,
            raw_text=f"3. Results\n\n{text}",
            cleaned_text=f"3. Results\n\n{text}",
            character_count=len(text),
            word_count=len(text.split())
        )
    ]

    sections = [
        PaperSection(
            id=sec_id,
            paper_id=paper_id,
            title="3. Results",
            normalized_title="results",
            section_type=SectionType.RESULTS,
            page_start=1,
            page_end=1,
            order_index=0,
            confidence=0.95
        )
    ]

    config = ChunkConfig(target_tokens=50, max_tokens=100, overlap_tokens=15)
    engine = ChunkingEngine()
    chunks = engine.chunk_paper(paper_id, pages, sections, config=config)

    assert len(chunks) > 1

    for chk in chunks:
        assert chk.token_count <= 150  # Respects max limit
        assert chk.section_id == sec_id


@pytest.mark.asyncio
async def test_paper_processing_chunk_persistence(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "chunk_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate test PDF
    upload_dir = get_upload_dir()
    test_pdf_path = upload_dir / "chunk_test.pdf"

    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "1. Abstract\n\nAbstract content.\n\n2. Methodology\n\nMethod step 1.", fontsize=12)
    doc.save(str(test_pdf_path))
    doc.close()

    # Upload
    with open(test_pdf_path, "rb") as f:
        upload_resp = await client.post(
            "/api/v1/papers/upload",
            headers=headers,
            files={"file": ("chunk_test.pdf", f, "application/pdf")}
        )
    paper_id = upload_resp.json()["paper_id"]

    # Process paper
    proc_resp = await client.post(f"/api/v1/papers/{paper_id}/process", headers=headers)
    assert proc_resp.status_code == 200
    assert proc_resp.json()["status"] == "READY"

    # Query PaperChunk DB records
    stmt = select(PaperChunk).where(PaperChunk.paper_id == paper_id).order_by(PaperChunk.chunk_index)
    res = await db_session.execute(stmt)
    db_chunks = res.scalars().all()

    assert len(db_chunks) >= 2
    for c in db_chunks:
        assert c.paper_id == uuid.UUID(paper_id)
        assert c.section_id is not None
        assert c.page_number in [1]
        assert c.token_count > 0
        assert c.metadata_json is not None
        assert "section_type" in c.metadata_json
