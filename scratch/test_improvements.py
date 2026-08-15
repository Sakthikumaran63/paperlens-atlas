"""
PaperLens Improvements Verification Suite
-------------------------------------------
Tests the 6 core architectural improvements:
1. Cookie-based Authentication & /auth/me profile hydration
2. Systematic Workspace Isolation (Anti-IDOR -> 404 on cross-user access)
3. Citation Quote Verification (Exact & RapidFuzz validation)
4. BM25 Keyword Scoring in Structure-Aware Retrieval
5. Rate Limiting via Slowapi
6. Pipeline Reconciler & Retry Endpoints
"""
import asyncio
import os
import sys
import time
import httpx

sys.path.insert(0, os.path.abspath("backend"))

BASE = "http://127.0.0.1:8000/api/v1"


async def main():
    print("=" * 70)
    print("RUNNING PAPERLENS IMPROVEMENTS TEST SUITE")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as client:
        # --- TEST 1: Cookie-Based Authentication & /auth/me ---
        print("\n[TEST 1] Testing Cookie-Based Authentication & /auth/me...")
        user_a_email = f"usera_{int(time.time())}@paperlens.ai"
        user_a_pass = "SecurePass123!"
        reg_resp = await client.post("/auth/register", json={
            "email": user_a_email,
            "password": user_a_pass,
            "name": "User Alpha"
        })
        assert reg_resp.status_code == 201, f"Register failed: {reg_resp.text}"
        
        # Check that cookie was set
        cookies = reg_resp.cookies
        has_token_cookie = "paperlens_token" in cookies
        print(f"  Cookie 'paperlens_token' set on register: {has_token_cookie}")
        assert has_token_cookie, "Expected httpOnly paperlens_token cookie to be set!"

        # Call /auth/me relying ONLY on cookie (no Authorization header)
        me_resp = await client.get("/auth/me")
        assert me_resp.status_code == 200, f"/auth/me failed with cookie: {me_resp.text}"
        me_data = me_resp.json()
        assert me_data["email"] == user_a_email
        print(f"  ✅ /auth/me successfully hydrated user profile via cookie: {me_data['email']}")

        # --- TEST 2: Workspace Isolation (Anti-IDOR -> 404 on Cross-User Access) ---
        print("\n[TEST 2] Testing Systematic Workspace Isolation (Anti-IDOR)...")
        # User A uploads a paper
        dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT /F1 12 Tf 72 712 Td (Abstract: Sand grain analysis) ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000216 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n322\n%%EOF"
        
        upload_resp = await client.post(
            "/papers/upload",
            files={"file": ("isolation_test.pdf", dummy_pdf_content, "application/pdf")}
        )
        assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
        paper_a_id = upload_resp.json()["paper_id"]
        print(f"  User A uploaded Paper ID: {paper_a_id}")

        # Register User B in a separate client session
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as client_b:
            user_b_email = f"userb_{int(time.time())}@paperlens.ai"
            await client_b.post("/auth/register", json={
                "email": user_b_email,
                "password": "SecurePass123!",
                "name": "User Beta"
            })

            # User B attempts to access User A's paper metadata
            idor_get = await client_b.get(f"/papers/{paper_a_id}")
            print(f"  User B GET /papers/{paper_a_id} -> Status: {idor_get.status_code}")
            assert idor_get.status_code == 404, f"Expected 404 Not Found (anti-IDOR), got: {idor_get.status_code}"

            # User B attempts to ask a question on User A's paper
            idor_qa = await client_b.post(f"/papers/{paper_a_id}/questions", json={"question": "What is the grain size?"})
            print(f"  User B POST /papers/{paper_a_id}/questions -> Status: {idor_qa.status_code}")
            assert idor_qa.status_code == 404, f"Expected 404 Not Found (anti-IDOR), got: {idor_qa.status_code}"

            # User B attempts to delete User A's paper
            idor_del = await client_b.delete(f"/papers/{paper_a_id}")
            print(f"  User B DELETE /papers/{paper_a_id} -> Status: {idor_del.status_code}")
            assert idor_del.status_code == 404, f"Expected 404 Not Found (anti-IDOR), got: {idor_del.status_code}"

            print("  ✅ Workspace Isolation verified: 404 Not Found returned on all cross-tenant access attempts (zero existence leakage).")

        # --- TEST 3: Citation Verification ---
        print("\n[TEST 3] Testing Citation Quote Verification (Exact & RapidFuzz)...")
        import importlib
        ev_mod = importlib.import_module("app.services.evidence_verification_service")
        EvidenceVerificationService = getattr(ev_mod, "EvidenceVerificationService")
        ver_svc = EvidenceVerificationService()

        sample_chunk = "SandSnap is a collaborative project for collecting and analyzing beach sand photographs."
        valid_quote = "SandSnap is a collaborative project"
        fuzzy_quote = "SandSnap is a colaborative project for collecting"
        fabricated_quote = "Quantum entanglement produces faster-than-light communication in silicon crystals."

        assert ver_svc.verify_quote(valid_quote, sample_chunk) is True, "Valid quote should pass verification"
        assert ver_svc.verify_quote(fuzzy_quote, sample_chunk) is True, "Fuzzy quote should pass verification"
        assert ver_svc.verify_quote(fabricated_quote, sample_chunk) is False, "Fabricated quote should fail verification"
        print("  ✅ Exact quote verification: PASSED")
        print("  ✅ Fuzzy (RapidFuzz >= 90) verification: PASSED")
        print("  ✅ Fabricated quote rejection: PASSED")

        # --- TEST 4: BM25 Keyword Scoring in Retrieval ---
        print("\n[TEST 4] Testing BM25 Keyword Scoring in Structure-Aware Retrieval...")
        ret_mod = importlib.import_module("app.services.retrieval_strategy_service")
        StructureAwareRetrievalService = getattr(ret_mod, "StructureAwareRetrievalService")
        strat_svc = StructureAwareRetrievalService()

        corpus = [
            "We propose a novel deep learning architecture using convolutional neural networks for shoreline detection.",
            "In this section we discuss historical background of grain size sieving and manual laboratory methods.",
            "Synthetic Aperture Radar satellite imagery provides high resolution backscatter measurements."
        ]
        bm25_res = strat_svc.calculate_bm25_scores("deep learning convolutional shoreline", corpus)
        print(f"  BM25 scores across corpus: {bm25_res}")
        assert bm25_res[0] > bm25_res[1], "Chunk 0 should score significantly higher than Chunk 1 for query"
        assert bm25_res[0] > bm25_res[2], "Chunk 0 should score significantly higher than Chunk 2 for query"
        print("  ✅ BM25 scoring correctly prioritized exact relevant chunk over unrelated chunks.")

        # --- TEST 5: Pipeline Retry Endpoint ---
        print("\n[TEST 5] Testing Pipeline Retry Endpoint...")
        retry_resp = await client.post(f"/papers/{paper_a_id}/retry")
        print(f"  Retry status: {retry_resp.status_code}, response: {retry_resp.json()}")
        assert retry_resp.status_code == 200
        assert retry_resp.json()["status"] == "PROCESSING"
        print("  ✅ Pipeline retry endpoint verified.")

        # --- TEST 6: Rate Limiting ---
        print("\n[TEST 6] Testing Rate Limiting via Slowapi on /auth/login...")
        rate_limited = False
        for i in range(25):
            try:
                login_attempt = await client.post(
                    "/auth/login",
                    json={"email": "nonexistent@paperlens.ai", "password": "wrong"}
                )
                if login_attempt.status_code == 429:
                    rate_limited = True
                    print(f"  Hit rate limit on attempt {i+1}: HTTP 429 Too Many Requests")
                    break
            except Exception as req_err:
                print(f"  Attempt {i+1} err: {req_err}")
                await asyncio.sleep(0.1)

        assert rate_limited, "Expected rate limit (HTTP 429) to trigger on rapid login attempts!"
        print("  ✅ Rate limiting verified successfully.")

    print("\n" + "=" * 70)
    print("ALL 6 ARCHITECTURAL IMPROVEMENTS VERIFIED AND PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
