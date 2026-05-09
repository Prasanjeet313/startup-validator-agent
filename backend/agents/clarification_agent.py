import json
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL
from backend.models.idea import IdeaBrief

def _client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

_QUESTION_SYSTEM = """You are an expert idea analyst helping validate startup and product ideas.
Your job is to ask sharp, targeted clarifying questions to deeply understand a raw idea before running market research.

Return ONLY a valid JSON object with this exact structure:
{
  "questions": ["question 1", "question 2", "question 3", "question 4", "question 5"]
}

Ask exactly 4-5 questions. Cover:
1. Who specifically is the target user — their job, lifestyle, or situation?
2. What exact pain do they feel today and how are they solving it (badly)?
3. Target geography or market (global, India, US, B2B, B2C, etc.)?
4. What existing alternatives exist and why are they not good enough?
5. How would this make money, or what value does it create?

Keep questions concise, not multi-part. One clear question per item."""

_BRIEF_SYSTEM = """You are an expert idea analyst. Based on the raw idea and the Q&A session,
synthesise a concise, structured Idea Brief that will guide market research.

Return ONLY a valid JSON object with this exact structure:
{
  "core_idea": "one clear sentence describing the product/service",
  "target_user": "specific user persona (e.g. 'remote software engineers aged 25-35')",
  "problem_being_solved": "the exact pain point in one sentence",
  "geography": "target market or geography",
  "unique_angle": "what makes this different from existing solutions",
  "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6"]
}

Keywords must be the best search terms to find real Reddit/YouTube discussions about this idea's problem space.
Mix broad pain terms, specific solution terms, and community terms."""


def get_clarifying_questions(raw_idea: str) -> list[str]:
    """Call GPT-4o with the raw idea, return 4-5 clarifying questions."""
    resp = _client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _QUESTION_SYSTEM},
            {"role": "user", "content": f"Raw idea: {raw_idea}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return json.loads(resp.choices[0].message.content)["questions"]


def build_idea_brief(raw_idea: str, questions: list[str], answers: list[str]) -> IdeaBrief:
    """Synthesise a structured Idea Brief from the original idea + Q&A session."""
    qa = "\n".join(
        f"Q{i + 1}: {q}\nA{i + 1}: {a}"
        for i, (q, a) in enumerate(zip(questions, answers))
    )
    resp = _client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _BRIEF_SYSTEM},
            {"role": "user", "content": f"Raw idea: {raw_idea}\n\nQ&A session:\n{qa}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return IdeaBrief(**json.loads(resp.choices[0].message.content))
