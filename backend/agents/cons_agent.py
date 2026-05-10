import json
from backend.llm_provider import make_completion, resolve_api_key
from backend.models.idea import LLMConfig

_SYSTEM = """You are a devil's advocate analyst. Your task is to find FUNDAMENTAL CONTRADICTIONS
to the core idea — reasons why the premise itself might be flawed, misaligned with reality,
or solving a problem that doesn't actually exist in the way the founder imagines.

DO NOT list operational challenges (funding, competition, marketing). Instead, challenge:
- Is the assumed problem real or is the data telling a different story?
- Does the proposed solution match how users actually behave (not how they say they behave)?
- Is there a hidden behavioural, cultural, or structural reason users wouldn't adopt this?
- Does the scraped data contradict the founder's core assumption?
- Does the web research reveal a market reality that undermines the idea?

Examples of the RIGHT kind of con:
- "Idea: AI journaling for mental health. Contradiction: 60% of posts show users prefer venting
  to friends or therapists — they explicitly distrust apps with emotional data."
- "Idea: B2B expense tracker targeting employees. Contradiction: Reddit data shows the real pain
  is in finance/accounting teams, not employees — wrong target user."
- "Idea: productivity app for students. Contradiction: Wikipedia + web results show students
  overwhelmingly cite motivation/discipline as the core issue, not tooling."

Return ONLY a valid JSON object:
{
  "cons": [
    "Contradiction 1 — backed by specific data or web evidence",
    "Contradiction 2 — backed by specific data or web evidence"
  ]
}

Produce 4-6 deep contradictions. Each must challenge WHY the idea may not work."""


def run_cons_agent(
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
        temperature=0.5,
    )
    return json.loads(resp).get("cons", [])
