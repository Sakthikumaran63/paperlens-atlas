# PaperLens Evaluation Framework & Metrics Specification

## 1. 3-Way System Configurations

The evaluation framework (`EvaluationService`) empirical benchmark compares three distinct pipeline configurations:

1. **`BASELINE_RAG`**: Un-structured vector cosine similarity search + un-verified LLM generation.
2. **`STRUCTURE_AWARE_RAG`**: Structure-aware section-weighted retrieval + un-verified LLM generation.
3. **`STRUCTURE_AWARE_RAG_WITH_VERIFICATION`**: Complete PaperLens pipeline (Structure-aware retrieval + `EvidenceVerificationService` refusal override).

---

## 2. Evaluation Metrics

### 2.1 Retrieval Metrics
- **Recall@K**: Fraction of gold evidence chunks retrieved in Top-K candidates.
  $$\text{Recall@K} = \frac{|\text{Retrieved Top-K Chunks} \cap \text{Gold Chunks}|}{|\text{Gold Chunks}|}$$
- **Precision@K**: Fraction of retrieved Top-K candidates that match gold evidence.
  $$\text{Precision@K} = \frac{|\text{Retrieved Top-K Chunks} \cap \text{Gold Chunks}|}{K}$$
- **MRR (Mean Reciprocal Rank)**: Reciprocal rank of the first relevant gold evidence chunk.
  $$\text{MRR} = \frac{1}{\text{rank}_1}$$

### 2.2 Answer Quality Metrics
- **Semantic Similarity**: Word overlap Jaccard similarity between candidate answer and `gold_answer`.
- **Exact Match**: Binary $1.0$ if normalized candidate answer equals `gold_answer`, $0.0$ otherwise.
- **Human Eval Support**: Fraction of non-abstained candidate answers supported by evidence.

### 2.3 Grounding Metrics
- **Evidence Precision**: Fraction of cited answer evidence sources matching gold evidence.
- **Evidence Recall**: Fraction of gold evidence items cited in answer.
- **Unsupported Claim Rate**: Fraction of generated candidate claims lacking supporting evidence.

### 2.4 Abstention Metrics
- **Answerable Accuracy**: Fraction of answerable questions correctly answered (not abstained).
- **Unanswerable Detection**: Fraction of unanswerable questions correctly refused with standard abstention statement.
- **False-Answer Rate (Hallucination Rate)**: Fraction of unanswerable questions incorrectly answered factually.

---

## 3. Running Evaluation Benchmarks

To execute the benchmark CLI script against the database:

```bash
cd backend
python scripts/run_evaluation.py
```

Outputs machine-readable JSON evaluation report to `docs/evaluation/evaluation_results.json`.
