from pydantic import BaseModel
from typing import List, Optional


class LLMConfig(BaseModel):
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    api_key: Optional[str] = None


class IdeaInput(BaseModel):
    idea: str
    llm_config: LLMConfig = LLMConfig()


class AnswerInput(BaseModel):
    answers: List[str]


class IdeaBrief(BaseModel):
    core_idea: str
    target_user: str
    problem_being_solved: str
    geography: str
    unique_angle: str
    keywords: List[str]


class QueryPlan(BaseModel):
    reddit_queries: List[str]
    youtube_queries: List[str]
