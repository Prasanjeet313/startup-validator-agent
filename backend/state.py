from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class RunState:
    run_id: str
    raw_idea: str
    llm_config: Optional[Any] = None   # LLMConfig
    status: str = "awaiting_answers"
    # awaiting_answers | querying | scraping_reddit | analyzing | done | error
    questions: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    idea_brief: Optional[Any] = None   # IdeaBrief
    query_plan: Optional[Any] = None   # QueryPlan
    web_results: Optional[Any] = None   # dict from web_search_scraper
    excel_path: Optional[str] = None
    report: Optional[Any] = None       # ValidationReport
    error: Optional[str] = None


# In-memory store keyed by run_id — good enough for MVP / single-server demo
runs: dict[str, RunState] = {}
