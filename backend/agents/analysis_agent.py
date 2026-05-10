"""
Analysis orchestrator.

Reads the scraped Excel + web search results, builds shared context strings,
then fires 4 specialized agents in parallel threads:

  pros_agent   — demand signals backed by data
  cons_agent   — contradictions to the core idea premise
  swot_agent   — full SWOT analysis
  scoring_agent — scores, key quotes, reasoning, market insights

Results are merged into a single ValidationReport.
"""

import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.models.idea import IdeaBrief, LLMConfig
from backend.models.report import (
    ValidationReport, SentimentBreakdown, KPIs, WebFindings, WebResult,
)
from backend.agents.pros_agent import run_pros_agent
from backend.agents.cons_agent import run_cons_agent
from backend.agents.swot_agent import run_swot_agent
from backend.agents.scoring_agent import run_scoring_agent

log = logging.getLogger("analysis_orchestrator")


# ── Context builders ──────────────────────────────────────────────────────────

def _build_data_context(
    idea_brief: IdeaBrief,
    kpis: KPIs,
    sentiment: SentimentBreakdown,
    posts_df: pd.DataFrame,
    comments_df: pd.DataFrame,
) -> str:
    # Keep context compact so parallel calls don't exceed Groq's TPM limit
    top_posts = posts_df.nlargest(20, "score") if len(posts_df) > 0 else posts_df
    top_comments = comments_df.nlargest(40, "score") if len(comments_df) > 0 else comments_df

    posts_text = "\n\n".join(
        f"[Score:{int(r.get('score', 0))} | Pain:{r.get('pain_score', 0)} "
        f"| Sentiment:{r.get('sentiment', '?')} | r/{r.get('subreddit', '?')}]\n"
        f"Title: {r.get('title', '')}\n"
        f"Body: {str(r.get('body', ''))[:280]}"
        for _, r in top_posts.iterrows()
    ) or "No posts found."

    comments_text = "\n".join(
        f"• [{int(r.get('score', 0))} pts] {str(r.get('body', ''))[:180]}"
        for _, r in top_comments.iterrows()
    ) or "No comments found."

    top_subs = ", ".join(
        f"r/{s['subreddit']} ({s['post_count']} posts)"
        for s in kpis.top_subreddits[:8]
    )

    return f"""=== IDEA BRIEF ===
Core Idea: {idea_brief.core_idea}
Target User: {idea_brief.target_user}
Problem: {idea_brief.problem_being_solved}
Geography: {idea_brief.geography}
Unique Angle: {idea_brief.unique_angle}
Keywords: {', '.join(idea_brief.keywords)}

=== DATA STATISTICS ===
Total Posts Scraped: {kpis.total_posts}
Total Comments Scraped: {kpis.total_comments}
Average Upvotes: {kpis.avg_upvotes:.1f}
Average Pain Score: {kpis.avg_pain_score:.2f}
Feature Request Posts: {kpis.feature_request_count}
Pain Posts Ratio: {kpis.pain_posts_ratio:.1f}%
Subreddits Found: {kpis.subreddits_found}
Top Subreddits: {top_subs}
Sentiment: {sentiment.positive}% positive | {sentiment.neutral}% neutral | {sentiment.negative}% negative

=== TOP REDDIT POSTS (sorted by score, top 50) ===
{posts_text}

=== TOP COMMENTS (sorted by score, top 100) ===
{comments_text}"""


def _build_web_context(web_results: dict) -> str:
    wiki = web_results.get("wikipedia_summary", "")
    results = web_results.get("top_results", [])

    results_text = "\n".join(
        f"{i+1}. {r.get('title', '')} ({r.get('url', '')})\n   {r.get('snippet', '')[:300]}"
        for i, r in enumerate(results[:12])
    ) or "No web results found."

    return f"""=== WIKIPEDIA CONTEXT ===
{wiki or "No Wikipedia data found."}

=== WEB SEARCH RESULTS (DuckDuckGo) ===
{results_text}"""


# ── KPI / Sentiment computation ───────────────────────────────────────────────

def _compute_kpis(posts_df: pd.DataFrame, comments_df: pd.DataFrame) -> KPIs:
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

    pain_posts = (
        int((posts_df["pain_score"] > 0).sum())
        if total_posts > 0 and "pain_score" in posts_df.columns
        else 0
    )
    pain_ratio = round(pain_posts / total_posts * 100, 1) if total_posts > 0 else 0.0

    top_subs: list[dict] = []
    if total_posts > 0:
        sub_counts = posts_df["subreddit"].value_counts().head(10)
        top_subs = [
            {"subreddit": sub, "post_count": int(cnt)}
            for sub, cnt in sub_counts.items()
        ]

    return KPIs(
        total_posts=total_posts,
        total_comments=total_comments,
        avg_upvotes=round(avg_upvotes, 1),
        avg_pain_score=round(avg_pain, 2),
        feature_request_count=feat_count,
        subreddits_found=subs_found,
        top_subreddits=top_subs,
        pain_posts_ratio=pain_ratio,
    )


def _compute_sentiment(posts_df: pd.DataFrame) -> SentimentBreakdown:
    total = len(posts_df)
    if total > 0 and "sentiment" in posts_df.columns:
        pos = int((posts_df["sentiment"] == "positive").sum())
        neg = int((posts_df["sentiment"] == "negative").sum())
        neu = total - pos - neg
        return SentimentBreakdown(
            positive=round(pos / total * 100, 1),
            neutral=round(neu / total * 100, 1),
            negative=round(neg / total * 100, 1),
        )
    return SentimentBreakdown(positive=0.0, neutral=100.0, negative=0.0)


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze(
    run_id: str,
    excel_path: str,
    idea_brief: IdeaBrief,
    web_results: dict,
    llm_config: LLMConfig,
) -> ValidationReport:
    """
    Orchestrate all specialized agents in parallel and return a ValidationReport.
    """
    xl = pd.read_excel(excel_path, sheet_name=None)
    posts_df: pd.DataFrame = xl.get("reddit_posts", pd.DataFrame())
    comments_df: pd.DataFrame = xl.get("reddit_comments", pd.DataFrame())

    kpis = _compute_kpis(posts_df, comments_df)
    sentiment = _compute_sentiment(posts_df)

    data_context = _build_data_context(idea_brief, kpis, sentiment, posts_df, comments_df)
    web_context = _build_web_context(web_results)

    log.info("[%s] Launching 4 specialized agents in parallel", run_id)

    results: dict = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_pros_agent,    data_context, web_context, llm_config): "pros",
            executor.submit(run_cons_agent,    data_context, web_context, llm_config): "cons",
            executor.submit(run_swot_agent,    data_context, web_context, llm_config): "swot",
            executor.submit(run_scoring_agent, data_context, web_context, llm_config): "scoring",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
                log.info("[%s] Agent '%s' completed", run_id, key)
            except Exception as exc:
                log.exception("[%s] Agent '%s' failed: %s", run_id, key, exc)
                results[key] = None

    pros    = results.get("pros") or []
    cons    = results.get("cons") or []
    swot    = results.get("swot")
    scoring = results.get("scoring") or {}

    if swot is None:
        from backend.models.report import SWOT
        swot = SWOT(strengths=[], weaknesses=[], opportunities=[], threats=[])

    web_findings = WebFindings(
        wikipedia_summary=web_results.get("wikipedia_summary", ""),
        top_results=[
            WebResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
            )
            for r in web_results.get("top_results", [])[:12]
        ],
        key_insights=scoring.get("market_insights", []),
    )

    return ValidationReport(
        run_id=run_id,
        buzz_score=int(scoring.get("buzz_score", 0)),
        validation_score=int(scoring.get("validation_score", 0)),
        sentiment=sentiment,
        kpis=kpis,
        pros=pros,
        cons=cons,
        swot=swot,
        key_quotes=scoring.get("key_quotes", []),
        reasoning=scoring.get("reasoning", ""),
        web_findings=web_findings,
        market_insights=scoring.get("market_insights", []),
    )
