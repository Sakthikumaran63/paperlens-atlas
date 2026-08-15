"""
PaperLens Extraction LLM Router
--------------------------------
Used by SummaryService, ContributionExtractionService, and MethodologyExtractionService
to call an LLM for structured extraction tasks.

Provider priority:
1. OpenAI-compatible API (if LLM_API_KEY is set)
2. Google Gemini (if GEMINI_API_KEY is set)
3. Ollama local server (if OLLAMA_BASE_URL is reachable)
4. Offline deterministic fallback

This is separate from the QA AIRouter -- it handles JSON extraction tasks
(summaries, contributions, methodology) not grounded Q&A.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("paperlens")


async def call_extraction_llm(
    system_prompt: str,
    user_prompt: str,
    timeout: float = 60.0,
) -> Optional[str]:
    """
    Try providers in order. Returns raw JSON string on success, None on all failures.
    """
    # --- 1. OpenAI-compatible API ---
    if settings.LLM_API_KEY:
        result = await _call_openai_compatible(system_prompt, user_prompt, timeout)
        if result:
            return result

    # --- 2. Google Gemini ---
    if settings.GEMINI_API_KEY:
        result = await _call_gemini(system_prompt, user_prompt, timeout)
        if result:
            return result

    # --- 3. Ollama ---
    result = await _call_ollama(system_prompt, user_prompt, timeout)
    if result:
        return result

    return None


async def _call_openai_compatible(
    system_prompt: str,
    user_prompt: str,
    timeout: float,
) -> Optional[str]:
    try:
        url = f"{settings.LLM_API_BASE.rstrip('/')}/chat/completions"
        payload: Dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            logger.warning(f"OpenAI-compatible API returned {resp.status_code}")
    except Exception as exc:
        logger.warning(f"OpenAI-compatible extraction call failed: {exc}")
    return None


async def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    timeout: float,
) -> Optional[str]:
    """Call Gemini generateContent API with automatic failover across all configured keys (PL_01 to PL_04)."""
    raw_keys = settings.GEMINI_API_KEYS.split(",") if settings.GEMINI_API_KEYS else []
    keys = [k.strip() for k in raw_keys if k.strip()]
    if not keys and settings.GEMINI_API_KEY:
        keys = [settings.GEMINI_API_KEY.strip()]

    if not keys:
        return None

    primary_model = settings.GEMINI_MODEL or "gemini-flash-latest"
    candidate_models = [primary_model, "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash-lite"]
    # De-duplicate while preserving order
    models_to_try = list(dict.fromkeys(candidate_models))

    combined_prompt = (
        f"{system_prompt}\n\n---\n\n{user_prompt}\n\n"
        "IMPORTANT: Return ONLY valid JSON. No markdown fences, no extra text."
    )
    payload = {
        "contents": [{"parts": [{"text": combined_prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }

    for model in models_to_try:
        for idx, key in enumerate(keys):
            key_id = f"PL_{idx+1:02d}"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        # Clean markdown codeblocks if any
                        if text.startswith("```"):
                            text = text.split("\n", 1)[-1].rsplit("\n", 1)[0].strip()
                        json.loads(text)  # validate parseable
                        logger.info(f"Gemini extraction succeeded using model [{model}] with key [{key_id}]")
                        return text
                    logger.warning(f"Gemini API model [{model}] with key [{key_id}] returned {resp.status_code}: {resp.text[:150]}")
            except json.JSONDecodeError:
                logger.warning(f"Gemini [{model}/{key_id}] returned non-JSON content for extraction task")
            except Exception as exc:
                logger.warning(f"Gemini [{model}/{key_id}] extraction call failed: {exc}")

    return None


async def _call_ollama(
    system_prompt: str,
    user_prompt: str,
    timeout: float,
) -> Optional[str]:
    """Call Ollama /api/chat endpoint with JSON format mode."""
    try:
        base = settings.OLLAMA_BASE_URL.rstrip("/")
        model = settings.OLLAMA_MODEL or "llama3.2"
        url = f"{base}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                text = resp.json()["message"]["content"].strip()
                json.loads(text)  # validate
                return text
            logger.warning(f"Ollama returned {resp.status_code}")
    except json.JSONDecodeError:
        logger.warning("Ollama returned non-JSON content for extraction task")
    except Exception as exc:
        logger.debug(f"Ollama not reachable or failed: {exc}")
    return None
