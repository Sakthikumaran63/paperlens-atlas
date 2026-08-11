"""Offline fallbacks for AI features, used when no LLM/embedding API key is
configured (typically local development).

Two independent heuristics live here:

1. `generate_offline_embedding` — a deterministic, dependency-free
   pseudo-embedding built from hashed token features (a "hashing trick"
   feature vector, TF-weighted, L2-normalized to unit length). It is NOT a
   semantically meaningful embedding in the way a real model's output is —
   it exists so that similarity search, storage, and pipeline code all work
   end-to-end locally without hitting an external API or requiring a large
   local model. Same text -> same vector, every time, on every machine.

2. `generate_offline_summary` — a rule-based extractive summarizer that
   maps a paper's already-extracted sections onto the 10 structured
   analysis fields the rest of the app expects, using section-title
   keyword matching and simple sentence heuristics rather than an LLM.

Neither of these tries to be "good" in the way a real model would be —
they exist to keep the pipeline fully functional (extract -> structure ->
chunk -> embed -> analyze -> ready) with zero external dependencies.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

# --------------------------------------------------------------------------
# Shared text utilities
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# A short, generic stopword list used only to down-weight low-signal tokens
# in the embedding heuristic — not meant to be linguistically exhaustive.
_STOPWORDS = frozenset(
    """
    a an the and or but if then else for of to in on at by with without
    is are was were be been being this that these those it its as from
    into over under between about above below up down out off again
    further not no nor so than too very can will just should now we our
    you your i he she they them their his her which who whom what when
    where why how all any both each few more most other some such only
    own same do does did doing have has had having
    """.split()
)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _stable_hash_int(value: str) -> int:
    """Deterministic hash, stable across processes/machines (unlike Python's
    built-in `hash()`, which is salted per-process for security)."""
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


# --------------------------------------------------------------------------
# 1. Deterministic pseudo-embeddings
# --------------------------------------------------------------------------

def generate_offline_embedding(text: str, dim: int = 1536) -> list[float]:
    """Deterministically derive an L2-normalized `dim`-length vector from `text`.

    Method (a lightweight, dependency-free feature-hashing / TF scheme):
      - Tokenize into unigrams and adjacent-word bigrams.
      - Each token/bigram is hashed (SHA-256, so it's stable across runs and
        machines) to a target dimension index and a +/- sign, à la the
        hashing trick used in large-scale linear models.
      - Weight = sublinear term-frequency scaling (`1 + log(count)`) times a
        stopword discount, so a handful of "the"/"and" repeats don't
        dominate the vector. Bigrams are weighted lower than unigrams since
        they mainly add phrase-level texture.
      - The resulting vector is L2-normalized to unit length, matching the
        convention of real embedding APIs (cosine similarity == dot product).

    Same `text` always produces the exact same vector; different text
    produces different (though not semantically meaningful) vectors.
    """
    if dim <= 0:
        raise ValueError("dim must be a positive integer")

    tokens = _tokenize(text)
    vec = [0.0] * dim

    if tokens:
        _accumulate_ngram_features(vec, tokens, n=1, weight_scale=1.0)
        if len(tokens) > 1:
            _accumulate_ngram_features(vec, tokens, n=2, weight_scale=0.5)

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        # Degenerate case: empty/whitespace-only text, or (astronomically
        # unlikely) perfect cancellation of hashed features. Fall back to a
        # full per-dimension hash of the raw text so we still return a
        # valid, deterministic unit vector instead of dividing by zero.
        vec = _dense_hash_vector(text, dim)
        norm = math.sqrt(sum(v * v for v in vec))

    return [v / norm for v in vec]


def _accumulate_ngram_features(
    vec: list[float],
    tokens: Sequence[str],
    *,
    n: int,
    weight_scale: float,
) -> None:
    dim = len(vec)
    ngrams: dict[str, int] = {}
    if n == 1:
        for tok in tokens:
            ngrams[tok] = ngrams.get(tok, 0) + 1
    else:
        for a, b in zip(tokens, tokens[1:]):
            key = f"{a}_{b}"
            ngrams[key] = ngrams.get(key, 0) + 1

    for gram, count in ngrams.items():
        stopword_discount = 0.15 if (n == 1 and gram in _STOPWORDS) else 1.0
        tf_weight = 1.0 + math.log(count)
        weight = tf_weight * stopword_discount * weight_scale

        idx_hash = _stable_hash_int(f"idx:{n}:{gram}")
        sign_hash = _stable_hash_int(f"sign:{n}:{gram}")

        idx = idx_hash % dim
        sign = 1.0 if (sign_hash % 2 == 0) else -1.0

        vec[idx] += sign * weight


def _dense_hash_vector(text: str, dim: int) -> list[float]:
    """Fallback: derive every dimension directly from a hash of `text`.

    Only used when the token-hashing path above produces an all-zero vector
    (empty input). O(dim) hash calls, so it's intentionally not the primary
    path for normal-length text.
    """
    vec = []
    for i in range(dim):
        digest = hashlib.sha256(f"{text}|{i}".encode("utf-8")).digest()
        as_unit_interval = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
        vec.append(as_unit_interval * 2.0 - 1.0)  # map [0, 1] -> [-1, 1]
    return vec


# --------------------------------------------------------------------------
# 2. Fallback structured paper summary
# --------------------------------------------------------------------------

SUMMARY_FIELDS: tuple[str, ...] = (
    "Executive Summary",
    "Problem Statement",
    "Objective",
    "Methodology",
    "Key Contributions",
    "Dataset",
    "Experimental Setup",
    "Key Results",
    "Limitations",
    "Conclusion",
)

_NOT_AVAILABLE = "Not available (insufficient extracted text for this section)."

# Section-title keywords used to locate the most relevant extracted section
# for each output field. Order matters: first matching keyword wins.
_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Executive Summary": ("abstract", "summary"),
    "Problem Statement": ("introduction", "motivation", "background", "problem"),
    "Objective": ("introduction", "abstract", "overview"),
    "Methodology": ("method", "methodology", "approach", "model", "architecture"),
    "Key Contributions": ("contribution", "introduction", "abstract"),
    "Dataset": ("dataset", "data", "corpus"),
    "Experimental Setup": ("experiment", "experimental setup", "implementation", "setup", "training"),
    "Key Results": ("result", "results", "evaluation", "findings"),
    "Limitations": ("limitation", "discussion", "future work"),
    "Conclusion": ("conclusion", "concluding", "summary"),
}

# Sentence-level keywords used to prioritize which sentences get pulled out
# of a matched section (falls back to the section's first sentences if none
# of these appear).
_SENTENCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Problem Statement": ("problem", "challenge", "however", "lack of", "gap", "difficult"),
    "Objective": ("we propose", "we present", "we aim", "goal", "objective", "this paper", "we introduce"),
    "Key Contributions": ("contribution", "we propose", "novel", "first to", "introduce"),
    "Dataset": ("dataset", "corpus", "collected", "samples", "instances"),
    "Key Results": ("%", "accuracy", "outperform", "improve", "achieves", "state-of-the-art", "result"),
    "Limitations": ("limitation", "future work", "does not capture", "fails to", "cannot", "constrain", "drawback", "shortcoming"),
}

SectionsInput = Union[Mapping[str, str], Iterable[Any]]


def generate_offline_summary(sections: SectionsInput) -> dict[str, str]:
    """Produce the 10 structured summary fields from extracted paper sections.

    `sections` accepts either:
      - a mapping of `{section_title: section_text}`, or
      - an iterable of objects/dicts with `.title`/`["title"]` and
        `.content`/`["content"]` (matching a typical `Section` ORM row or
        its serialized form).

    Always returns all 10 keys in `SUMMARY_FIELDS`; any field that can't be
    derived from the available text is set to a clear "not available"
    placeholder rather than being omitted, so downstream consumers can rely
    on a stable schema.
    """
    normalized = _normalize_sections(sections)
    all_text = " ".join(normalized.values())

    result: dict[str, str] = {}
    for field in SUMMARY_FIELDS:
        result[field] = _extract_field(field, normalized, all_text)
    return result


def _normalize_sections(sections: SectionsInput) -> dict[str, str]:
    if isinstance(sections, Mapping):
        return {str(title): (text or "") for title, text in sections.items() if (text or "").strip()}

    normalized: dict[str, str] = {}
    for item in sections:
        if isinstance(item, Mapping):
            title = item.get("title") or item.get("heading") or item.get("name") or "Untitled"
            text = item.get("content") or item.get("text") or ""
        else:
            title = getattr(item, "title", None) or getattr(item, "heading", None) or "Untitled"
            text = getattr(item, "content", None) or getattr(item, "text", None) or ""
        if text and text.strip():
            normalized[str(title)] = text
    return normalized


def _extract_field(field: str, sections: dict[str, str], all_text: str) -> str:
    if not all_text.strip():
        return _NOT_AVAILABLE

    sentence_keywords = _SENTENCE_KEYWORDS.get(field)

    if sentence_keywords:
        # Search across ALL sections (in order) for sentences matching this
        # field's keywords first — the right sentence is often in a section
        # whose *title* wouldn't have matched (e.g. a "novel method" claim
        # sitting in the Abstract, not a dedicated "Contributions" section).
        global_hit = _sentences_with_keywords_across_sections(sections, sentence_keywords, max_sentences=2)
        if global_hit:
            return global_hit

    # No sentence-level keyword hit (or this field doesn't use them) — fall
    # back to whichever section's *title* best matches this field.
    section_text = _find_section_text(sections, _SECTION_KEYWORDS.get(field, ())) or all_text

    if sentence_keywords:
        extracted = _sentences_with_keywords(section_text, sentence_keywords, max_sentences=2)
    else:
        extracted = _first_sentences(section_text, max_sentences=3)

    return extracted or _NOT_AVAILABLE


def _sentences_with_keywords_across_sections(
    sections: dict[str, str], keywords: tuple[str, ...], max_sentences: int
) -> str:
    matched: list[str] = []
    for text in sections.values():
        for sentence in _split_sentences(text):
            if any(kw in sentence.lower() for kw in keywords):
                matched.append(sentence)
            if len(matched) >= max_sentences:
                return " ".join(matched).strip()
    return " ".join(matched).strip()


def _find_section_text(sections: dict[str, str], keywords: tuple[str, ...]) -> Optional[str]:
    for keyword in keywords:
        for title, text in sections.items():
            if keyword in title.lower():
                return text
    return None


def _first_sentences(text: str, max_sentences: int) -> str:
    sentences = _split_sentences(text)
    return " ".join(sentences[:max_sentences]).strip()


def _sentences_with_keywords(text: str, keywords: tuple[str, ...], max_sentences: int) -> str:
    sentences = _split_sentences(text)
    matched = [s for s in sentences if any(kw in s.lower() for kw in keywords)]
    if not matched:
        return _first_sentences(text, max_sentences)
    return " ".join(matched[:max_sentences]).strip()


# --------------------------------------------------------------------------
# 3. Offline extractive Q&A
# --------------------------------------------------------------------------

def generate_offline_answer(
    question_text: str,
    evidence_items: Sequence[Mapping[str, Any]],
    max_sentences: int = 8,
) -> dict[str, Any]:
    """Produce a best-effort extractive answer from evidence chunks.

    This is NOT a substitute for a real LLM — it exists so that Q&A works
    end-to-end locally when no LLM API key is configured.

    Strategy:
    1. Tokenize the question into keywords (minus stopwords).
    2. Score each sentence in the evidence by how many question keywords it
       contains.
    3. Select the top-scoring sentences (deduped, ordered by original
       position) as the answer.
    4. Return the evidence IDs used so the pipeline can build citation links.

    Returns a dict matching `LLMAnswerOutput` shape:
        {"answer": str, "evidence_ids": list[str], "confidence": float, "abstain": bool}
    """
    if not evidence_items:
        return {
            "answer": "I couldn't find enough information in the uploaded paper to answer this reliably.",
            "evidence_ids": [],
            "confidence": 0.0,
            "abstain": True,
        }

    # Build question keywords
    q_tokens = [t for t in _tokenize(question_text) if t not in _STOPWORDS and len(t) > 2]
    if not q_tokens:
        q_tokens = _tokenize(question_text)[:10]

    # Score every sentence across all evidence items
    scored: list[tuple[float, str, str]] = []  # (score, sentence, evidence_id)
    for item in evidence_items:
        text = item.get("text", "")
        eid = item.get("evidence_id", "")
        for sentence in _split_sentences(text):
            s_lower = sentence.lower()
            # Count how many question keywords appear
            hits = sum(1 for kw in q_tokens if kw in s_lower)
            # Bonus for longer informative sentences (diminishing)
            word_count = len(sentence.split())
            length_bonus = min(0.3, word_count / 100.0)
            score = hits + length_bonus
            if score > 0:
                scored.append((score, sentence, eid))

    # Sort by score descending, take top sentences
    scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate sentences
    seen_sents: set[str] = set()
    selected: list[tuple[str, str]] = []
    for _, sent, eid in scored:
        normalized = sent.strip().lower()
        if normalized not in seen_sents:
            seen_sents.add(normalized)
            selected.append((sent, eid))
            if len(selected) >= max_sentences:
                break

    if not selected:
        # If no keyword matches, take first sentences from top evidence items
        for item in evidence_items[:3]:
            text = item.get("text", "")
            eid = item.get("evidence_id", "")
            for sent in _split_sentences(text)[:2]:
                selected.append((sent, eid))
            if len(selected) >= max_sentences:
                break

    if not selected:
        return {
            "answer": "I couldn't find enough information in the uploaded paper to answer this reliably.",
            "evidence_ids": [],
            "confidence": 0.0,
            "abstain": True,
        }

    # Build answer text
    answer_parts = [s for s, _ in selected]
    answer_text = "Based on the paper: " + " ".join(answer_parts)

    # Collect unique evidence IDs used
    used_eids = list(dict.fromkeys(eid for _, eid in selected if eid))

    # Confidence proportional to how many keywords were covered
    if q_tokens:
        answer_lower = answer_text.lower()
        covered = sum(1 for kw in q_tokens if kw in answer_lower)
        confidence = min(0.85, covered / len(q_tokens))
    else:
        confidence = 0.4

    return {
        "answer": answer_text,
        "evidence_ids": used_eids,
        "confidence": round(confidence, 3),
        "abstain": False,
    }

