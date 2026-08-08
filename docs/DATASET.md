# PaperLens Benchmark Dataset Specification

## 1. Overview & Purpose

The PaperLens Evaluation Benchmark is a standardized research dataset designed to evaluate structure-aware retrieval, grounded answer generation, evidence attribution, and controlled abstention performance across scientific papers.

---

## 2. Dataset Schema & Structure

Each evaluation dataset consists of an `EvaluationDataset` containing a list of `EvaluationQuestionItem` records:

```json
{
  "dataset_name": "PaperLens Scientific QA Benchmark",
  "items": [
    {
      "id": "q_001",
      "paper_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "question": "What dataset was used for evaluating performance?",
      "question_type": "DATASET",
      "gold_answer": "ImageNet and WMT 2014 translation datasets.",
      "gold_evidence": [
        {
          "page": 5,
          "section": "Experiments",
          "text": "We evaluate on WMT 2014 English-to-German translation dataset...",
          "chunk_id": "c_102"
        }
      ],
      "page": 5,
      "section": "Experiments",
      "answerable": true
    },
    {
      "id": "q_002",
      "paper_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "question": "What stock market price ticker was analyzed in this paper?",
      "question_type": "UNKNOWN",
      "gold_answer": "I couldn't find enough information in the uploaded paper to answer this reliably.",
      "gold_evidence": [],
      "page": null,
      "section": null,
      "answerable": false
    }
  ]
}
```

---

## 3. Question Difficulty Taxonomy

1. **Easy (Direct Stated)**: Answer is explicitly stated in a single sentence within a primary section (e.g. dataset name in `Experiments`).
2. **Moderate (Section-Localized)**: Answer requires combining two adjacent sentences within the same section.
3. **Difficult (Multi-Section Cross-Reference)**: Answer requires synthesizing information across multiple sections (e.g. comparing proposed architecture in `Methodology` with baseline results in `Results`).
4. **Unanswerable (Out-of-Scope / Absent)**: Question asks for details completely absent from the paper (e.g. training carbon footprint or unrelated domain details). The system must abstain.

---

## 4. Provenance & Evidence Attribution

Every gold evidence item retains four explicit fields:
- `page`: Page number in original PDF ($1$-indexed)
- `section`: Scientific section title (e.g. `"Methodology"`, `"Experiments"`)
- `text`: Exact textual passage snippet
- `chunk_id`: Optional UUID of database chunk
