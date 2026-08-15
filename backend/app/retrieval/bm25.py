"""
BM25 Keyword Retrieval Module
-----------------------------
Computes normalized BM25Okapi lexical relevance scores across candidate texts.
"""
import re
from typing import List


class BM25Retriever:
    """Computes BM25Okapi keyword scores normalized to [0, 1]."""

    @staticmethod
    def score_candidates(query: str, candidate_texts: List[str]) -> List[float]:
        if not query or not candidate_texts:
            return [0.0] * len(candidate_texts)

        try:
            from rank_bm25 import BM25Okapi
            tokenized_corpus = [re.findall(r'\b[a-zA-Z0-9]{2,}\b', t.lower()) for t in candidate_texts]
            bm25 = BM25Okapi(tokenized_corpus)
            query_tokens = re.findall(r'\b[a-zA-Z0-9]{2,}\b', query.lower())
            if not query_tokens:
                return [0.0] * len(candidate_texts)
            scores = bm25.get_scores(query_tokens)
            max_score = max(scores) if len(scores) and max(scores) > 0 else 1.0
            return [float(s / max_score) for s in scores]
        except Exception:
            # Fallback to lexical token overlap
            q_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower()))
            if not q_words:
                return [0.0] * len(candidate_texts)
            results = []
            for t in candidate_texts:
                t_words = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', t.lower()))
                overlap = len(q_words.intersection(t_words)) / len(q_words)
                results.append(float(overlap))
            return results
