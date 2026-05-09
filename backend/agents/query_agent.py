import json
from backend.llm_provider import make_completion, resolve_api_key
from backend.models.idea import IdeaBrief, QueryPlan, LLMConfig

_SYSTEM = """You are a market research strategist. Generate search queries that surface real user pain,
demand, complaints, and discussions about a startup idea's problem space.

Reddit queries should find:
- Authentic complaints and frustrations ("hate X", "X is broken", "struggling with X")
- People seeking solutions ("best app for X", "is there a tool for X", "how to X")
- Feature requests ("wish there was", "someone should build", "why isn't there X")
- Community discussions about this problem space

YouTube queries are also generated but will be used in the next phase — still return them as they will be cached.

Return ONLY a valid JSON object:
{
  "reddit_queries": ["query1", "query2", "query3", "query4", "query5", "query6", "query7"],
  "youtube_queries": ["query1", "query2", "query3", "query4", "query5", "query6"]
}

Generate 6-8 Reddit queries and 5-6 YouTube queries.
Queries must be natural language phrases people actually type, not keyword stuffing.
Cover different angles: pain, solution-seeking, existing alternatives, specific use cases."""


def generate_query_plan(idea_brief: IdeaBrief, llm_config: LLMConfig) -> QueryPlan:
    """Generate optimised Reddit + YouTube search queries from an Idea Brief."""
    brief_text = (
        f"Core idea: {idea_brief.core_idea}\n"
        f"Target user: {idea_brief.target_user}\n"
        f"Problem: {idea_brief.problem_being_solved}\n"
        f"Geography: {idea_brief.geography}\n"
        f"Unique angle: {idea_brief.unique_angle}\n"
        f"Keywords: {', '.join(idea_brief.keywords)}"
    )
    key = resolve_api_key(llm_config.provider, llm_config.api_key)
    resp = make_completion(
        llm_config.provider,
        llm_config.model,
        key,
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": brief_text},
        ],
        temperature=0.5,
    )
    return QueryPlan(**json.loads(resp))
