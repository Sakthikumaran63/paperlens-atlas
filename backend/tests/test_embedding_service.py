import fitz
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaperStatus
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.embedding_service import EmbeddingGenerationError, EmbeddingService
from app.services.indexing_service import index_paper
from app.utils.storage import get_upload_dir


class MockHTTPClient:
    """Mock HTTPX client to simulate OpenAI-compatible embedding API without external network calls."""
    def __init__(self, status_code: int = 200, raise_exception: bool = False):
        self.status_code = status_code
        self.raise_exception = raise_exception

    async def post(self, url: str, json: dict = None, headers: dict = None):
        if self.raise_exception:
            raise httpx.RequestError("Mock network connection error")

        if self.status_code != 200:
            return httpx.Response(self.status_code, text="Mock API Error")

        inputs = json.get("input", [])
        mock_data = []
        for idx, text in enumerate(inputs):
            # Deterministic mock 1536-dim vector based on index
            vector = [float(idx + 0.1)] * 1536
            mock_data.append({"index": idx, "embedding": vector})

        return httpx.Response(200, json={"data": mock_data, "model": json.get("model")})


@pytest.mark.asyncio
async def test_embedding_service_mock_generation():
    mock_client = MockHTTPClient(status_code=200)
    service = EmbeddingService(http_client=mock_client)

    texts = ["Sample scientific abstract text.", "Methodology paragraph text."]
    embeddings = await service.generate_embeddings(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1536
    assert len(embeddings[1]) == 1536
    assert embeddings[0][0] == 0.1
    assert embeddings[1][0] == 1.1


@pytest.mark.asyncio
async def test_embedding_service_error_handling():
    mock_client = MockHTTPClient(status_code=500)
    service = EmbeddingService(http_client=mock_client)

    with pytest.raises(EmbeddingGenerationError) as exc_info:
        await service.generate_embeddings(["Test text"])

    assert "Embedding API returned status code 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_indexing_pipeline_and_pgvector_storage(
    client: AsyncClient,
    db_session: AsyncSession
):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "indexer_user@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate sample PDF & process text extraction
    upload_dir = get_upload_dir()
    test_pdf_path = upload_dir / "indexing_test.pdf"

    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "1. Abstract\n\nAbstract text for vector indexing.\n\n2. Methods\n\nMethod step 1.", fontsize=12)
    doc.save(str(test_pdf_path))
    doc.close()

    # Upload & Process
    with open(test_pdf_path, "rb") as f:
        upload_resp = await client.post(
            "/api/v1/papers/upload",
            headers=headers,
            files={"file": ("indexing_test.pdf", f, "application/pdf")}
        )
    paper_id = upload_resp.json()["paper_id"]

    await client.post(f"/api/v1/papers/{paper_id}/process", headers=headers)

    # 1. Run index_paper service using MockHTTPClient
    mock_service = EmbeddingService(http_client=MockHTTPClient(status_code=200))
    indexed_paper = await index_paper(paper_id, db_session, embedding_service=mock_service)

    assert indexed_paper.status == PaperStatus.READY
    assert indexed_paper.processing_error is None

    # Verify vector embeddings saved in PaperChunk DB records
    chunk_stmt = select(PaperChunk).where(PaperChunk.paper_id == paper_id).order_by(PaperChunk.chunk_index)
    res = await db_session.execute(chunk_stmt)
    chunks = res.scalars().all()

    assert len(chunks) >= 2
    for c in chunks:
        assert c.embedding is not None
        assert len(c.embedding) == 1536

    # 2. Test skipping already embedded chunks unless force_reindex=True
    # Pass mock client that throws error if called
    fail_client = MockHTTPClient(status_code=500)
    fail_service = EmbeddingService(http_client=fail_client)

    # Re-indexing without force_reindex should skip API call and succeed instantly
    skip_paper = await index_paper(paper_id, db_session, force_reindex=False, embedding_service=fail_service)
    assert skip_paper.status == PaperStatus.READY

    # 3. Test force_reindex=True with failing client -> status FAILED & safe processing_error
    failed_paper = await index_paper(paper_id, db_session, force_reindex=True, embedding_service=fail_service)
    assert failed_paper.status == PaperStatus.FAILED
    assert failed_paper.processing_error is not None
    assert "Embedding indexing failed" in failed_paper.processing_error
    assert "Traceback" not in failed_paper.processing_error

    # 4. Test retry success
    retry_paper = await index_paper(paper_id, db_session, force_reindex=True, embedding_service=mock_service)
    assert retry_paper.status == PaperStatus.READY
    assert retry_paper.processing_error is None
