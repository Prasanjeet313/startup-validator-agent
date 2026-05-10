import json
from backend.llm_provider import make_completion, resolve_api_key
from backend.models.idea import LLMConfig

_SYSTEM = """You are the final judge synthesising a startup idea validation report.
Your task: assign scores, extract key quotes, write reasoning, and distil market insights.

BUZZ SCORE (0-100): volume and spread of online discussion
  0  = nobody talks about this problem space
  50 = moderate niche discussion
  100 = trending topic everywhere

VALIDATION SCORE (0-100): strength of genuine demand and pain signal
  0  = problem doesn't exist or people don't care
  50 = real pain but existing solutions acceptable
  100 = people desperately need this, nothing adequate exists

KEY QUOTES: 6-10 verbatim or near-verbatim quotes from the posts/comments that best
illustrate demand, pain, or attitudes. Pick quotes that are vivid and specific.

REASONING: 4-5 sentence paragraph. Cite specific numbers. Connect scores to evidence.
Conclude with a clear verdict: is this worth pursuing?

MARKET INSIGHTS: 4-6 high-level insights combining Reddit data + web research.
These should give a founder a realistic picture of the market landscape.

Return ONLY a valid JSON object:
{
  "buzz_score": <integer 0-100>,
  "validation_score": <integer 0-100>,
  "key_quotes": ["verbatim quote 1", ...],
  "reasoning": "4-5 sentence paragraph with evidence and verdict.",
  "market_insights": ["insight 1", "insight 2", ...]
}"""


def run_scoring_agent(
    data_context: str,
    web_context: str,
    llm_config: LLMConfig,
) -> dict:
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
        temperature=0.3,
    )
    return json.loads(resp)
