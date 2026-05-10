from pydantic import BaseModel
from typing import List, Dict, Any


class SentimentBreakdown(BaseModel):
    positive: float
    neutral: float
    negative: float


class KPIs(BaseModel):
    total_posts: int
    total_comments: int
    avg_upvotes: float
    avg_pain_score: float
    feature_request_count: int
    subreddits_found: int
    top_subreddits: List[Dict[str, Any]] = []   # [{"subreddit": str, "post_count": int}]
    pain_posts_ratio: float = 0.0               # % of posts with pain_score > 0


class SWOT(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]


class WebResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebFindings(BaseModel):
    wikipedia_summary: str = ""
    top_results: List[WebResult] = []
    key_insights: List[str] = []


class ValidationReport(BaseModel):
    run_id: str
    buzz_score: int
    validation_score: int
    sentiment: SentimentBreakdown
    kpis: KPIs
    pros: List[str]
    cons: List[str]
    swot: SWOT
    key_quotes: List[str]
    reasoning: str
    web_findings: WebFindings
    market_insights: List[str] = []
