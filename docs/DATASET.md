# PaperLens Atlas — Scientific Paper Dataset Catalog & Integration Strategy

This document outlines the dataset strategy for **PaperLens Atlas**, including public dataset catalogs, benchmark schemas, and implementation guides for ingesting open-access datasets (QASper, S2ORC, SciFact, PubMedQA) into PaperLens Atlas.

---

## 1. Catalog of Public Scientific Datasets

### 1.1 QASper (Question Answering on Scientific Papers)

* **Source**: [Hugging Face (`allenai/qasper`)](https://huggingface.co/datasets/allenai/qasper) | [Semantic Scholar](https://allenai.org/data/qasper)
* **Domain**: Computer Science (NLP, Artificial Intelligence, Machine Learning)
* **Size**: 1,593 full-text arXiv papers, 5,049 questions, 7,993 evidence-grounded answers.
* **License**: CC-BY 4.0
* **PaperLens Integration**:
  - **Structure-Aware RAG**: QASper questions explicitly map to sections (`Abstract`, `Methodology`, `Results`).
  - **Evidence Verification & Abstention**: Includes exact paragraph evidence spans and unanswerable questions to benchmark refusal accuracy.

```python
from datasets import load_dataset

# Load QASper dataset from Hugging Face
dataset = load_dataset("allenai/qasper")

sample_paper = dataset["train"][0]
print(f"Paper Title: {sample_paper['title']}")
print(f"Total Sections: {len(sample_paper['full_text']['section_name'])}")
```

---

### 1.2 S2ORC (Semantic Scholar Open Research Corpus)

* **Source**: [AI2 S2ORC GitHub](https://github.com/allenai/s2orc) | [Hugging Face (`allenai/s2orc`)](https://huggingface.co/datasets/allenai/s2orc)
* **Domain**: Multi-disciplinary (Computer Science, BioMed, Physics, Chemistry)
* **Size**: 8.1M+ full-text open access papers.
* **License**: CC-BY 4.0
* **PaperLens Integration**:
  - **Structure Extraction**: Provides pre-parsed full text with explicit section headings, body paragraphs, and figure/table captions.
  - **Section Detector Calibration**: Used to train and evaluate `SectionDetector`.

---

### 1.3 SciFact (Scientific Claim Verification)

* **Source**: [Hugging Face (`allenai/scifact`)](https://huggingface.co/datasets/allenai/scifact)
* **Domain**: BioMed & Computer Science
* **Size**: 1,409 scientific claims with evidence rationale sentences and stance labels (`SUPPORTS`, `REFUTES`, `NOT_ENOUGH_INFO`).
* **License**: CC-BY-NC 4.0
* **PaperLens Integration**:
  - **Claim Lineage**: Benchmarks `EvidenceSelectionService` and `EvidenceVerificationService`.

---

### 1.4 PubMedQA (Biomedical Grounded Q&A)

* **Source**: [Hugging Face (`pubmed_qa`)](https://huggingface.co/datasets/pubmed_qa)
* **Domain**: Biomedical & Life Sciences
* **Size**: 1,000 expert-annotated QA pairs + 211.5k unlabeled QA pairs.
* **License**: MIT
* **PaperLens Integration**:
  - Benchmarks domain-specific QA performance across medical and life science papers.

---

## 2. Dataset Strategy & Usage in PaperLens Atlas

### Strategy 1: Benchmark Dataset Converter (`scripts/ingest_qasper_benchmark.py`)
Convert QASper papers and QA pairs into the PaperLens `EvaluationDataset` JSON schema for automated evaluation via `EvaluationService`.

```python
import uuid
from datasets import load_dataset
import json

def convert_qasper_to_paperlens(limit=10):
    dataset = load_dataset("allenai/qasper", split="train")
    items = []
    
    for paper in list(dataset)[:limit]:
        paper_id = str(uuid.uuid4())
        for q_item in paper["qas"]["question"]:
            items.append({
                "id": str(uuid.uuid4()),
                "paper_id": paper_id,
                "question": q_item,
                "question_type": "GENERAL",
                "gold_answer": "Extracted ground truth answer",
                "gold_evidence": [],
                "answerable": True
            })
            
    with open("docs/evaluation/qasper_benchmark.json", "w") as f:
        json.dump({"dataset_name": "QASper Benchmark", "items": items}, f, indent=2)

if __name__ == "__main__":
    convert_qasper_to_paperlens()
```

### Strategy 2: Offline Fallback & Testing
Use deterministic offline embeddings and summaries (`generate_offline_embedding`, `generate_offline_summary`) to run 100% of benchmark tests without API costs or internet dependency.

### Strategy 3: Multi-Domain Benchmark Matrix
Evaluate PaperLens across Computer Science (QASper), BioMed (PubMedQA), and General Science (SciFact) to ensure broad cross-domain accuracy.

---

## 3. Dataset Summary Matrix

| Dataset | Primary Role | Size | Recommended Ingestion Strategy |
| :--- | :--- | :--- | :--- |
| **QASper** | Grounded Q&A & Evidence Selection | ~120 MB | Script converter (`ingest_qasper_benchmark.py`) |
| **S2ORC** | Section Detection & Structure RAG | Streaming | Parquet / PostgreSQL bulk import |
| **SciFact** | Evidence Verification & Refusal | ~15 MB | Direct JSON test fixture |
| **PubMedQA** | Biomedical Domain Validation | ~85 MB | SQLite test fixture |
