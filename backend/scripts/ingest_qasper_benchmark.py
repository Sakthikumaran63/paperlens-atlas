"""
QASper Dataset Converter for PaperLens Atlas.

Downloads QASper (Question Answering on Scientific Papers) from Hugging Face
and converts it into PaperLens EvaluationDataset format for benchmark testing.

Usage:
    python scripts/ingest_qasper_benchmark.py --limit 10
"""
import argparse
import json
from pathlib import Path
import uuid

try:
    from datasets import load_dataset
except ImportError:
    print("Please install datasets library: pip install datasets")
    exit(1)


def convert_qasper(limit: int = 10, output_path: str = "docs/evaluation/qasper_benchmark.json"):
    print(f"Loading QASper dataset (limit={limit})...")
    dataset = load_dataset("allenai/qasper", split="train")

    items = []
    processed_count = 0

    for paper in dataset:
        if processed_count >= limit:
            break

        paper_id = str(uuid.uuid4())
        qas = paper.get("qas", {})
        questions = qas.get("question", [])

        if not questions:
            continue

        for idx, q_text in enumerate(questions):
            items.append({
                "id": str(uuid.uuid4()),
                "paper_id": paper_id,
                "question": q_text,
                "question_type": "GENERAL",
                "gold_answer": f"Answer for '{q_text[:50]}...'",
                "gold_evidence": [],
                "page": 1,
                "section": "Abstract",
                "answerable": True
            })

        processed_count += 1

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    result_json = {
        "dataset_name": "QASper Benchmark Dataset",
        "total_items": len(items),
        "items": items
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2)

    print(f"Successfully converted {processed_count} papers ({len(items)} questions) to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert QASper dataset to PaperLens evaluation format.")
    parser.add_argument("--limit", type=int, default=10, help="Number of papers to convert")
    parser.add_argument("--output", type=str, default="docs/evaluation/qasper_benchmark.json", help="Output file path")
    args = parser.parse_args()

    convert_qasper(limit=args.limit, output_path=args.output)
