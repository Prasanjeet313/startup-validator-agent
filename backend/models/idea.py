from pydantic import BaseModel
from typing import List


class IdeaInput(BaseModel):
    idea: str


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
    youtube_queries: List[str]   # generated but not used until YouTube is wired in
