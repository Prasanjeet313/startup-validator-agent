import json
import pandas as pd
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL
from backend.models.idea import IdeaBrief
from backend.models.report import ValidationReport, SentimentBreakdown, KPIs

def _client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

_SYSTEM = """You are a senior market research analyst. You have been given real social data scraped from Reddit
about a startup idea. Analyze it and produce a structured validation report.

Rules:
- Every claim must be grounded in the data. Cite numbers. Quote real users.
- Do NOT write generic platitudes like "there is demand" without evidence.
- Buzz Score = volume and spread of discussion (0=nobody, 100=everywhere).
- Validation Score = real pain and demand signal (0=nobody cares, 100=people desperately need this).

Return ONLY a valid JSON object:
{
  "buzz_score": <integer 0-100>,
  "validation_score": <integer 0-100>,
  "pros": ["specific pro backed by data", ...],
  "cons": ["specific con backed by data", ...],
  "key_quotes": ["verbatim or near-verbatim quote from a post or comment", ...],
  "reasoning": "3-4 sentence paragraph: explain your scores with specific evidence, what the data shows, and your overall conclusion."
}

pros: 4-6 items. cons: 3-5 items. key_quotes: 5-8 real quotes that best illustrate demand or pain."""


def analyze(run_id: str, excel_path: str, idea_brief: IdeaBrief) -> ValidationReport:
    """Read scraped Excel data and produce a full ValidationReport."""
    xl = pd.read_excel(excel_path, sheet_name=None)
    posts_df: pd.DataFrame = xl.get("reddit_posts", pd.DataFrame())
    comments_df: pd.DataFrame = xl.get("reddit_comments", pd.DataFrame())

    # ── Compute KPIs directly from raw data ──────────────────────────────────
    total_posts = len(posts_df)
    total_comments = len(comments_df)
    avg_upvotes = float(posts_df["score"].mean()) if total_posts > 0 else 0.0
    avg_pain = (
        float(posts_df["pain_score"].mean())
        if total_posts > 0 and "pain_score" in posts_df.columns
        else 0.0
    )
    feat_count = (
        int((posts_df["feature_request_flag"].astype(str).str.strip() != "").sum())
        if total_posts > 0 and "feature_request_flag" in posts_df.columns
        else 0
    )
    subs_found = int(posts_df["subreddit"].nunique()) if total_posts > 0 else 0

    kpis = KPIs(
        total_posts=total_posts,
        total_comments=total_comments,
        avg_upvotes=round(avg_upvotes, 1),
        avg_pain_score=round(avg_pain, 2),
        feature_request_count=feat_count,
        subreddits_found=subs_found,
    )

    # ── Compute Sentiment from rule-based scraper tags ───────────────────────
    if total_posts > 0 and "sentiment" in posts_df.columns:
        pos = int((posts_df["sentiment"] == "positive").sum())
        neg = int((posts_df["sentiment"] == "negative").sum())
        neu = total_posts - pos - neg
        sentiment = SentimentBreakdown(
            positive=round(pos / total_posts * 100, 1),
            neutral=round(neu / total_posts * 100, 1),
            negative=round(neg / total_posts * 100, 1),
        )
    else:
        sentiment = SentimentBreakdown(positive=0.0, neutral=100.0, negative=0.0)

    # ── Build LLM prompt from top posts + comments ───────────────────────────
    top_posts = (
        posts_df.nlargest(25, "score") if total_posts > 0 else posts_df
    )
    top_comments = (
        comments_df.nlargest(40, "score") if total_comments > 0 else comments_df
    )

    posts_text = "\n\n".join(
        f"[Score:{int(r.get('score', 0))} | Pain:{r.get('pain_score', 0)} "
        f"| Sentiment:{r.get('sentiment', '?')} | r/{r.get('subreddit', '?')}]\n"
        f"Title: {r.get('title', '')}\n"
        f"Body: {str(r.get('body', ''))[:400]}"
        for _, r in top_posts.iterrows()
    ) or "No posts found."

    comments_text = "\n".join(
        f"• {str(r.get('body', ''))[:250]}"
        for _, r in top_comments.iterrows()
    ) or "No comments found."

    prompt = f"""Idea: {idea_brief.core_idea}
Target User: {idea_brief.target_user}
Problem: {idea_brief.problem_being_solved}

--- DATA STATS ---
Posts scraped: {total_posts}
Comments scraped: {total_comments}
Avg upvotes: {avg_upvotes:.1f}
Avg pain score: {avg_pain:.2f}
Feature request posts: {feat_count}
Subreddits found: {subs_found}
Sentiment breakdown: {sentiment.positive}% positive | {sentiment.neutral}% neutral | {sentiment.negative}% negative

--- TOP REDDIT POSTS (sorted by score) ---
{posts_text}

--- TOP COMMENTS (sorted by score) ---
{comments_text}"""

    resp = _client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    data = json.loads(resp.choices[0].message.content)

    return ValidationReport(
        run_id=run_id,
        buzz_score=int(data["buzz_score"]),
        validation_score=int(data["validation_score"]),
        sentiment=sentiment,
        kpis=kpis,
        pros=data["pros"],
        cons=data["cons"],
        key_quotes=data["key_quotes"],
        reasoning=data["reasoning"],
    )
