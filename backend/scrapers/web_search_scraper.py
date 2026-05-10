"""
Web search scraper — no API key required.

Sources:
  DuckDuckGo  : duckduckgo-search package (pip install duckduckgo-search)
  Wikipedia   : wikipedia package (pip install wikipedia)

Both are free, rate-limit-friendly, and require zero credentials.
"""

import logging
from backend.models.idea import IdeaBrief

log = logging.getLogger("web_search")


def _ddg_search(query: str, max_results: int = 10) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results
    except Exception as exc:
        log.warning("DuckDuckGo search failed for '%s': %s", query, exc)
        return []


def _wiki_search(query: str) -> str:
    try:
        import wikipedia
        hits = wikipedia.search(query, results=3)
        if not hits:
            return ""
        page = wikipedia.page(hits[0], auto_suggest=False)
        return page.summary[:2500]
    except Exception as exc:
        log.warning("Wikipedia search failed for '%s': %s", query, exc)
        return ""


def run_web_search(idea_brief: IdeaBrief) -> dict:
    """
    Run DuckDuckGo + Wikipedia searches for the idea.

    Returns:
        {
            "wikipedia_summary": str,
            "top_results": [{"title", "url", "snippet"}, ...]
        }
    """
    core = idea_brief.core_idea
    problem = idea_brief.problem_being_solved
    kws = " ".join(idea_brief.keywords[:4])

    log.info("Web search — Wikipedia: %s", core)
    wiki_summary = _wiki_search(core)

    log.info("Web search — DuckDuckGo core idea")
    idea_results = _ddg_search(f"{core} {problem}", max_results=8)

    log.info("Web search — DuckDuckGo market/competition")
    market_results = _ddg_search(f"{kws} market size startup", max_results=5)

    log.info("Web search — DuckDuckGo blog/expert opinions")
    opinion_results = _ddg_search(f"{kws} review blog opinion", max_results=5)

    # Deduplicate by URL
    seen: set[str] = set()
    all_results: list[dict] = []
    for r in idea_results + market_results + opinion_results:
        if r["url"] and r["url"] not in seen:
            seen.add(r["url"])
            all_results.append(r)

    return {
        "wikipedia_summary": wiki_summary,
        "top_results": all_results[:15],
    }
