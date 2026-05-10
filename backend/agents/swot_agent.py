import json
from backend.llm_provider import make_completion, resolve_api_key
from backend.models.idea import LLMConfig
from backend.models.report import SWOT

_SYSTEM = """You are a strategic analyst performing a SWOT analysis on a startup idea.
Ground every point in the Reddit data, KPI stats, and web research provided.

STRENGTHS  — genuine demand signals, community size, expressed pain that the idea solves
WEAKNESSES — data-backed gaps, low engagement signals, contradictions in what users say vs do
OPPORTUNITIES — market gaps visible in discussions, underserved segments, adjacent use cases,
                trends visible in web research that favour this idea
THREATS    — competition signals in posts, adoption barriers users mention, macro threats
             from web/Wikipedia research

Rules:
- 3-5 items per quadrant
- Each item must reference concrete evidence (post counts, quotes, web findings, subreddit names)
- No generic business-school statements — everything grounded in the data

Return ONLY a valid JSON object:
{
  "strengths":     ["evidence-backed strength 1", ...],
  "weaknesses":    ["evidence-backed weakness 1", ...],
  "opportunities": ["evidence-backed opportunity 1", ...],
  "threats":       ["evidence-backed threat 1", ...]
}"""


def run_swot_agent(
    data_context: str,
    web_context: str,
    llm_config: LLMConfig,
) -> SWOT:
    key = resolve_api_key(llm_config.provider, llm_config.api_key)
    prompt = f"{data_context}\n\n{web_context}"
    resp = make_completion(
        llm_config.provider,
        llm_config.model,
        key,
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    data = json.loads(resp)
    return SWOT(
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        opportunities=data.get("opportunities", []),
        threats=data.get("threats", []),
    )
