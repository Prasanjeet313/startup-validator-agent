from pydantic import BaseModel
from typing import List


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


class ValidationReport(BaseModel):
    run_id: str
    buzz_score: int
    validation_score: int
    sentiment: SentimentBreakdown
    kpis: KPIs
    pros: List[str]
    cons: List[str]
    key_quotes: List[str]
    reasoning: str
