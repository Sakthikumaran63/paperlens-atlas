import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("paperlens")

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_RECOMMENDATIONS_URL = "https://api.semanticscholar.org/recommendations/v1/papers/forpaper"
CROSSREF_API_URL = "https://api.crossref.org/works"


class SemanticScholarService:
    """
    Service for fetching academic paper recommendations using Semantic Scholar API
    with automatic CrossRef fallback when rate limited or unindexed.
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "PaperLens-Academic-Client/1.0 (https://paperlens.ai; mailto:research@paperlens.ai)"
        }

    async def fetch_related_papers_by_title(
        self, seed_title: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetches related academic papers given a seed paper title.
        
        1. Attempts Semantic Scholar Graph search & recommendations endpoints.
        2. If Semantic Scholar rate limits (429) or returns no recommendations,
           gracefully falls back to CrossRef REST API for high-availability paper discovery.
        """
        if not seed_title or not seed_title.strip():
            return []

        clean_title = seed_title.strip()

        # Step 1: Try Semantic Scholar API
        s2_papers = await self._fetch_semantic_scholar(clean_title, limit)
        if s2_papers:
            return s2_papers

        # Step 2: Fallback to CrossRef API
        logger.info(f"Using CrossRef fallback search for title: '{clean_title}'")
        return await self._fetch_crossref(clean_title, limit)

    async def _fetch_semantic_scholar(
        self, seed_title: str, limit: int
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self.headers, follow_redirects=True
        ) as client:
            try:
                search_params = {
                    "query": seed_title,
                    "limit": 1,
                    "fields": "title,paperId",
                }
                search_res = await client.get(
                    SEMANTIC_SCHOLAR_SEARCH_URL, params=search_params
                )

                if search_res.status_code == 429:
                    logger.warning(
                        f"Semantic Scholar API rate-limited (429) for '{seed_title}'. Failing over to CrossRef."
                    )
                    return []

                search_res.raise_for_status()
                search_data = search_res.json()

                results = search_data.get("data", [])
                if not results or not results[0].get("paperId"):
                    return []

                paper_id = results[0]["paperId"]
                rec_url = f"{SEMANTIC_SCHOLAR_RECOMMENDATIONS_URL}/{paper_id}"
                rec_params = {
                    "limit": limit,
                    "fields": "title,year,abstract,authors,url",
                }
                rec_res = await client.get(rec_url, params=rec_params)

                if rec_res.status_code == 429:
                    return []

                rec_res.raise_for_status()
                rec_data = rec_res.json()
                recommended_papers = rec_data.get("recommendedPapers", [])

                clean_papers: List[Dict[str, Any]] = []
                for paper in recommended_papers:
                    raw_authors = paper.get("authors") or []
                    authors_list = [
                        a.get("name") for a in raw_authors if a and a.get("name")
                    ]
                    clean_papers.append(
                        {
                            "title": paper.get("title") or "Untitled",
                            "year": paper.get("year"),
                            "abstract": paper.get("abstract"),
                            "authors": authors_list,
                            "url": paper.get("url"),
                        }
                    )
                return clean_papers

            except Exception as exc:
                logger.warning(
                    f"Semantic Scholar lookup encountered error: {exc}. Proceeding to fallback."
                )
                return []

    async def _fetch_crossref(
        self, seed_title: str, limit: int
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self.headers, follow_redirects=True
        ) as client:
            try:
                params = {"query": seed_title, "rows": limit}
                res = await client.get(CROSSREF_API_URL, params=params)
                res.raise_for_status()

                items = res.json().get("message", {}).get("items", [])
                clean_papers: List[Dict[str, Any]] = []

                for item in items:
                    titles = item.get("title", [])
                    t = titles[0] if titles else "Untitled"

                    date_parts = (
                        item.get("issued", {}).get("date-parts", [[None]])[0]
                    )
                    year = date_parts[0] if date_parts else None

                    authors = []
                    for a in item.get("author", []):
                        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                        if name:
                            authors.append(name)

                    abstract_raw = item.get("abstract") or ""
                    # Strip basic HTML/JATS XML tags if present in CrossRef abstracts
                    import re
                    clean_abstract = re.sub(r"<[^>]+>", "", abstract_raw).strip() if abstract_raw else None

                    url = item.get("URL")

                    clean_papers.append(
                        {
                            "title": t,
                            "year": year,
                            "abstract": clean_abstract,
                            "authors": authors,
                            "url": url,
                        }
                    )
                return clean_papers

            except Exception as exc:
                logger.error(f"CrossRef lookup failed: {exc}", exc_info=True)
                return []
