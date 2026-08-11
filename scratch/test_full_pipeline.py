"""
PaperLens Full Pipeline Test - Robust Version
-----------------------------------------------
1. Register / login test user
2. Upload papers ONE AT A TIME with delay between uploads
3. Wait for each to reach READY before uploading the next
4. Run a grounded Q&A question per paper
5. Print results summary
"""
import asyncio
import os
import time
import httpx

BASE = "http://localhost:8000/api/v1"
PAPER_DIR = r"D:\sakthi\paperlens-atlas\backend\Data\base paper"

# Questions tailored to each paper
PAPER_QUESTIONS = {
    "1-s2.0-S0378383924001029-main.pdf": "What is SandSnap and how does it map grain sizes from images?",
    "applsci-13-03268-v2.pdf": "What machine learning models or remote sensing techniques were reviewed for shoreline monitoring?",
    "Earth Surf Processes Landf - 2023 - Matsumoto - Development of an automated mobile grain size mapping of a mixed sediment.pdf": "How does the automated mobile system perform grain size mapping on mixed sediment beaches?",
    "esurf-10-349-2022.pdf": "What are the key findings about coastal dynamics and sediment transport in this study?",
    "jmse-12-00172.pdf": "How are drone images used for particle size prediction in this research?",
    "remotesensing-16-01763.pdf": "How is SAR remote sensing applied to estimate gravel beach grain size?",
}


async def wait_for_ready(client, paper_id, headers, fname, timeout=180):
    """Poll status endpoint until paper is READY or fails."""
    start = time.time()
    while (time.time() - start) < timeout:
        try:
            sr = await client.get(f"/papers/{paper_id}/status", headers=headers)
            if sr.status_code == 200:
                data = sr.json()
                st = data.get("status", "UNKNOWN")
                progress = data.get("progress", 0)
                stage = data.get("stage", "")
                if st == "READY":
                    elapsed = time.time() - start
                    print(f"    [OK] {fname}: READY in {elapsed:.1f}s")
                    return True
                elif st in ("FAILED", "ERROR"):
                    err_msg = data.get("error_message", "unknown error")
                    print(f"    [FAIL] {fname}: {st} - {err_msg}")
                    return False
                else:
                    print(f"    ... {fname}: {st} stage={stage} progress={progress}%")
        except Exception as e:
            print(f"    [WARN] Poll error: {e}")

        await asyncio.sleep(4)

    print(f"    [TIMEOUT] {fname}: did not reach READY in {timeout}s")
    return False


async def main():
    timeout_cfg = httpx.Timeout(180.0, connect=30.0)
    async with httpx.AsyncClient(base_url=BASE, timeout=timeout_cfg) as client:
        # --- Step 1: Register or Login ---
        print("=" * 60)
        print("STEP 1: Authentication")
        print("=" * 60)
        email = f"pipeline.tester.{int(time.time())}@gmail.com"
        password = "TestPass123!"
        name = "Pipeline Tester"

        reg = await client.post("/auth/register", json={
            "email": email, "password": password, "name": name
        })
        if reg.status_code == 201:
            token = reg.json()["access_token"]
            print(f"  [OK] Registered new user: {email}")
        else:
            login = await client.post("/auth/login", json={
                "email": email, "password": password
            })
            if login.status_code == 200:
                token = login.json()["access_token"]
                print(f"  [OK] Logged in: {email}")
            else:
                print(f"  [FAIL] Auth failed: {login.status_code} {login.text}")
                return

        headers = {"Authorization": f"Bearer {token}"}

        # --- Check if papers already exist ---
        print("\n" + "=" * 60)
        print("STEP 2: Check Existing Papers")
        print("=" * 60)

        existing_resp = await client.get("/papers", headers=headers)
        existing_papers = {}
        if existing_resp.status_code == 200:
            for p in existing_resp.json():
                existing_papers[p.get("file_name", "")] = {
                    "id": p.get("id"),
                    "status": p.get("status"),
                }
                print(f"  Found: {p.get('file_name', 'N/A')} -> {p.get('status', 'N/A')}")

        # --- Step 3: Upload papers one at a time ---
        print("\n" + "=" * 60)
        print("STEP 3: Upload & Process Base Papers (sequential)")
        print("=" * 60)

        pdfs = sorted([f for f in os.listdir(PAPER_DIR) if f.lower().endswith(".pdf")])
        uploaded = {}  # filename -> paper_id

        for i, fname in enumerate(pdfs, 1):
            # Check if already uploaded and READY
            if fname in existing_papers:
                ep = existing_papers[fname]
                if ep["status"] == "READY":
                    print(f"\n  [{i}/{len(pdfs)}] {fname}")
                    print(f"    [SKIP] Already READY (ID: {ep['id']})")
                    uploaded[fname] = ep["id"]
                    continue

            fpath = os.path.join(PAPER_DIR, fname)
            fsize_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"\n  [{i}/{len(pdfs)}] Uploading: {fname} ({fsize_mb:.1f} MB)")

            try:
                with open(fpath, "rb") as f:
                    resp = await client.post(
                        "/papers/upload",
                        headers=headers,
                        files={"file": (fname, f, "application/pdf")},
                    )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    pid = data.get("id") or data.get("paper_id")
                    uploaded[fname] = pid
                    print(f"    [OK] Uploaded -> ID: {pid}")

                    # Wait for this paper to process before uploading next
                    print(f"    Waiting for processing...")
                    ready = await wait_for_ready(client, pid, headers, fname)
                    if not ready:
                        print(f"    [WARN] Paper not ready, continuing anyway")

                    # Small delay before next upload
                    if i < len(pdfs):
                        await asyncio.sleep(2)
                else:
                    print(f"    [FAIL] Upload failed: {resp.status_code} {resp.text[:200]}")
            except Exception as e:
                print(f"    [ERROR] {e}")
                # Wait and retry once
                print(f"    Retrying in 5s...")
                await asyncio.sleep(5)
                try:
                    with open(fpath, "rb") as f:
                        resp = await client.post(
                            "/papers/upload",
                            headers=headers,
                            files={"file": (fname, f, "application/pdf")},
                        )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        pid = data.get("id") or data.get("paper_id")
                        uploaded[fname] = pid
                        print(f"    [OK] Retry succeeded -> ID: {pid}")
                        await wait_for_ready(client, pid, headers, fname)
                    else:
                        print(f"    [FAIL] Retry also failed: {resp.status_code}")
                except Exception as e2:
                    print(f"    [ERROR] Retry also failed: {e2}")

        # --- Step 4: Q&A on each paper ---
        print("\n" + "=" * 60)
        print("STEP 4: Grounded Q&A Tests")
        print("=" * 60)

        results = []
        for fname, pid in uploaded.items():
            question = PAPER_QUESTIONS.get(fname, "What are the main findings of this paper?")
            print(f"\n  Paper: {fname}")
            print(f"  Q: {question}")

            try:
                qa_resp = await client.post(
                    f"/papers/{pid}/questions",
                    headers=headers,
                    json={"question": question},
                )
                if qa_resp.status_code == 200:
                    qa_data = qa_resp.json()
                    answer = qa_data.get("answer", "")
                    sources = qa_data.get("sources", [])
                    abstained = qa_data.get("abstained", False)

                    if abstained:
                        print(f"  [ABSTAIN] Model abstained - insufficient evidence")
                        print(f"  Answer: {answer[:200]}")
                        results.append((fname, "ABSTAIN", answer[:100]))
                    else:
                        print(f"  [OK] Answer ({len(answer)} chars, {len(sources)} sources)")
                        print(f"  Answer: {answer[:300]}{'...' if len(answer) > 300 else ''}")
                        for s in sources[:3]:
                            pg = s.get('page', '?')
                            sec = s.get('section', 'N/A')
                            txt = s.get('text', '')[:80]
                            print(f"    Source [Page {pg}, {sec}]: {txt}...")
                        results.append((fname, "PASS", f"{len(answer)} chars, {len(sources)} sources"))
                else:
                    err = qa_resp.text[:200]
                    print(f"  [FAIL] Q&A failed: {qa_resp.status_code} {err}")
                    results.append((fname, "FAIL", f"HTTP {qa_resp.status_code}: {err}"))
            except Exception as e:
                print(f"  [ERROR] {e}")
                results.append((fname, "ERROR", str(e)[:100]))

        # --- Summary ---
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        for fname, result, detail in results:
            icon = "[PASS]" if result == "PASS" else "[FAIL]" if result in ("FAIL", "ERROR") else "[WARN]"
            short = fname[:55] + "..." if len(fname) > 55 else fname
            print(f"  {icon} {short:<58} {result:<10} {detail[:50]}")

        passed = sum(1 for _, r, _ in results if r in ("PASS", "ABSTAIN"))
        total = len(results)
        print(f"\n  Result: {passed}/{total} papers completed Q&A test")
        print(f"  Papers uploaded: {len(uploaded)}/{len(pdfs)}")


if __name__ == "__main__":
    asyncio.run(main())
