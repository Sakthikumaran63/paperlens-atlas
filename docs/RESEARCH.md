# PaperLens Research Novelty & Vision

## 1. Problem Statement & Generic RAG Limitations

Standard RAG architectures treat PDFs as plain un-structured text documents. They slice text into uniform character blocks (e.g. 500 characters with 50 character overlap), embed them into a vector space, and execute nearest-neighbor cosine similarity search:

```text
Generic RAG Pipeline:

PDF ──► Plain Text ──► Fixed Chunks ──► Embeddings ──► Top-K Cosine Search ──► Un-verified LLM Answer
```

### Critical Failure Modes of Generic RAG on Scientific Literature
1. **Loss of Structural Context**: Generic RAG treats text from `Related Work` identically to text from `Methodology` or `Results`. A question like *"What dataset was used?"* frequently retrieves historical datasets mentioned in `Related Work` rather than the paper's actual evaluation dataset.
2. **Citation Hallucinations**: Standard LLMs asked to cite page numbers or sections routinely fabricate plausible numbers because they lack direct binding to database provenance records.
3. **Over-Confidence & False Answering**: Generic RAG systems try to answer every question even when the uploaded paper contains zero relevant information (e.g., answering *"What stock market ticker was analyzed?"* on a computer vision paper).

---

## 2. Proposed Research Novelty

PaperLens introduces an evidence-grounded scientific document architecture combining three core technical innovations:

```text
PaperLens Architecture:

PDF ──► Section Taxonomy ──► Structure-Aware Chunks ──► Question Routing ──► Weighted Ranking ──► Verification ──► Grounded Answer / Abstention
```

### Core Research Contributions
1. **Structure-Aware Retrieval Routing with BM25 Keyword Scoring**: Question intent classification maps queries to a 14-type taxonomy (`DATASET`, `METHODOLOGY`, `RESULT`, `LIMITATION`, etc.) and dynamically adjusts retrieval scoring using a composite function combining semantic vector similarity, section taxonomy routing, and normalized BM25 Okapi keyword scoring:
   $$\text{final\_score} = (\text{semantic\_score} \times 0.60) + (\text{section\_score} \times 0.25) + (\text{bm25\_score} \times 0.15)$$
2. **Database Provenance Binding & Fuzzy Quote Verification**: Metadata (`page_number`, `section_title`, `chunk_id`) is owned exclusively by PostgreSQL / SQLite. Every cited quote is verified against source chunk content via exact substring matching and `RapidFuzz` partial ratio ($S_{\text{match}} \ge 90$) before persisting `AnswerEvidence` records. Fabricated quotes are rejected, preventing LLM citation fabrications.
3. **Controlled Uncertainty & Evidence Verification**: An explicit verification layer (`EvidenceVerificationService`) evaluates candidate answers against retrieved evidence package snippets. If the computed support score falls below threshold ($0.70$) or if no verifiable citations survive, the system forces a controlled abstention:
   *"I couldn't find enough information in the uploaded paper to answer this reliably."*

---

## 3. Experimental Hypotheses

- **Hypothesis 1 (Retrieval Precision)**: Structure-aware retrieval routing will achieve higher Recall@K and Precision@K than baseline vector RAG on domain-specific scientific questions (`DATASET`, `METHODOLOGY`, `METRIC`).
- **Hypothesis 2 (Hallucination Reduction)**: The evidence verification layer will significantly lower the unsupported claim rate and false-answer rate on unanswerable questions compared to un-verified LLM generation.
- **Hypothesis 3 (Abstention Accuracy)**: Controlled abstention will achieve $\ge 90\%$ unanswerable question detection accuracy without sacrificing answerable question accuracy.

---

## 4. Long-Term Vision

PaperLens aims to evolve from single-paper understanding into a **trust-oriented scientific knowledge graph**:

```text
Single Paper Understanding ──► Multi-Paper Comparative RAG ──► Evidence Knowledge Graph ──► Verifiable Literature Discovery
```
