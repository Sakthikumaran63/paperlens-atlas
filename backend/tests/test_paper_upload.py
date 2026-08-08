import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient):
    # 1. Register User & get token
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "pdf_uploader@example.com", "password": "Password123!", "name": "PDF Uploader"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock PDF file upload
    pdf_content = b"%PDF-1.5 %fake pdf header content for testing upload endpoint..."
    files = {
        "file": ("sample_research_paper.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    response = await client.post("/api/v1/papers/upload", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert "paper_id" in data
    assert data["file_name"] == "sample_research_paper.pdf"
    assert data["status"] == "UPLOADED"


@pytest.mark.asyncio
async def test_upload_non_pdf_rejection(client: AsyncClient):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "text_uploader@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    txt_content = b"This is a text file, not a PDF."
    files = {
        "file": ("document.txt", io.BytesIO(txt_content), "text/plain")
    }

    response = await client.post("/api/v1/papers/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported."


@pytest.mark.asyncio
async def test_upload_invalid_mime_rejection(client: AsyncClient):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "mime_uploader@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = {
        "file": ("document.pdf", io.BytesIO(b"%PDF-1.4 data"), "image/jpeg")
    }

    response = await client.post("/api/v1/papers/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported."


@pytest.mark.asyncio
async def test_upload_exceeds_max_size(client: AsyncClient):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "large_file@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate content > 20 MB (20 * 1024 * 1024 + 100 bytes)
    # Using io.BytesIO buffer
    oversized_content = b"%PDF-1.5 " + b"0" * (20 * 1024 * 1024 + 100)
    files = {
        "file": ("large_paper.pdf", io.BytesIO(oversized_content), "application/pdf")
    }

    response = await client.post("/api/v1/papers/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "File size exceeds maximum limit of 20 MB."


@pytest.mark.asyncio
async def test_upload_empty_file_rejection(client: AsyncClient):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "empty_file@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = {
        "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
    }

    response = await client.post("/api/v1/papers/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."


@pytest.mark.asyncio
async def test_list_and_get_paper_details(client: AsyncClient):
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "lister@example.com", "password": "Password123!"}
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload paper
    files = {"file": ("paper1.pdf", io.BytesIO(b"%PDF-1.5 test content"), "application/pdf")}
    upload_resp = await client.post("/api/v1/papers/upload", headers=headers, files=files)
    paper_id = upload_resp.json()["paper_id"]

    # 1. List papers
    list_resp = await client.get("/api/v1/papers", headers=headers)
    assert list_resp.status_code == 200
    papers_list = list_resp.json()
    assert len(papers_list) >= 1
    assert any(p["id"] == paper_id for p in papers_list)

    # 2. Get paper detail
    detail_resp = await client.get(f"/api/v1/papers/{paper_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == paper_id
    assert detail_resp.json()["file_name"] == "paper1.pdf"
    assert detail_resp.json()["status"] == "UPLOADED"


@pytest.mark.asyncio
async def test_delete_paper_and_unauthorized_access(client: AsyncClient):
    # User A
    user_a_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner_a@example.com", "password": "Password123!"}
    )
    token_a = user_a_reg.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B
    user_b_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "attacker_b@example.com", "password": "Password123!"}
    )
    token_b = user_b_reg.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A uploads paper
    files = {"file": ("private_a.pdf", io.BytesIO(b"%PDF-1.5 confidential"), "application/pdf")}
    upload_resp = await client.post("/api/v1/papers/upload", headers=headers_a, files=files)
    paper_id = upload_resp.json()["paper_id"]

    # User B attempts to DELETE User A's paper -> 404 / 403 Forbidden
    del_b_resp = await client.delete(f"/api/v1/papers/{paper_id}", headers=headers_b)
    assert del_b_resp.status_code == 404
    assert del_b_resp.json()["detail"] == "Paper not found or access denied."

    # User A DELETES User A's paper -> 200 OK
    del_a_resp = await client.delete(f"/api/v1/papers/{paper_id}", headers=headers_a)
    assert del_a_resp.status_code == 200
    assert del_a_resp.json()["paper_id"] == paper_id

    # Verify paper no longer exists
    get_resp = await client.get(f"/api/v1/papers/{paper_id}", headers=headers_a)
    assert get_resp.status_code == 404
