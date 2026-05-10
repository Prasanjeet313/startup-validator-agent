import json
from backend.llm_provider import make_completion, resolve_api_key
from backend.models.idea import LLMConfig

_SYSTEM = """You are a market validation analyst. Your ONLY task is to identify genuine strengths
and demand signals for a startup idea, backed exclusively by evidence from the provided data.

Rules:
- Every pro MUST cite specific evidence: numbers, percentages, direct user language, subreddit names
- Look for: expressed pain matching the idea's solution, community size, feature requests, positive sentiment
- Do NOT write generic statements like "there is clear demand" — prove it with data
- 5-7 specific, evidence-backed pros

Return ONLY a valid JSON object:
{
  "pros": [
    "Pro 1 — cite specific evidence from the data",
    "Pro 2 — cite specific evidence from the data"
  ]
}"""


def run_pros_agent(
    data_context: str,
    web_context: str,
    llm_config: LLMConfig,
) -> list[str]:
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
    return json.loads(resp).get("pros", [])
