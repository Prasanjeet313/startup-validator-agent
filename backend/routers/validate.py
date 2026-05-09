import uuid
import threading
import logging
from fastapi import APIRouter, HTTPException

from backend.models.idea import IdeaInput, AnswerInput
from backend.state import runs, RunState
from backend.agents.clarification_agent import get_clarifying_questions, build_idea_brief
from backend.agents.query_agent import generate_query_plan
from backend.agents.analysis_agent import analyze
from backend.scrapers.reddit_scraper import run_all_queries as reddit_scrape
from backend.storage.excel_writer import save_run

router = APIRouter()
log = logging.getLogger("pipeline")


def _pipeline(run_id: str) -> None:
    """
    Full research pipeline — runs in a background thread so the API stays responsive.

    YouTube hook: uncomment the two lines marked below and import youtube_scrape
    when the YouTube Data API key is added to .env.
    """
    state = runs[run_id]
    try:
        log.info("[%s] Stage 1/3 — generating search queries", run_id)
        state.status = "querying"
        state.query_plan = generate_query_plan(state.idea_brief)
        log.info(
            "[%s] Query plan ready — %d Reddit queries, %d YouTube queries",
            run_id,
            len(state.query_plan.reddit_queries),
            len(state.query_plan.youtube_queries),
        )

        log.info("[%s] Stage 2/3 — scraping Reddit", run_id)
        state.status = "scraping_reddit"
        posts, comments = reddit_scrape(run_id, state.query_plan.reddit_queries)
        log.info(
            "[%s] Reddit scrape done — %d posts, %d comments",
            run_id, len(posts), len(comments),
        )

        # ── YouTube hook (activate in Phase 1 later) ─────────────────────────
        # from backend.scrapers.youtube_scraper import run_all_queries as yt_scrape
        # yt_videos, yt_comments = yt_scrape(run_id, state.query_plan.youtube_queries)
        # Then pass yt_videos, yt_comments to save_run below.
        # ─────────────────────────────────────────────────────────────────────

        state.excel_path = save_run(run_id, posts, comments)
        log.info("[%s] Excel saved → %s", run_id, state.excel_path)

        log.info("[%s] Stage 3/3 — AI analysis", run_id)
        state.status = "analyzing"
        state.report = analyze(run_id, state.excel_path, state.idea_brief)
        log.info(
            "[%s] Analysis done — Buzz: %d, Validation: %d",
            run_id,
            state.report.buzz_score,
            state.report.validation_score,
        )

        state.status = "done"
        log.info("[%s] Pipeline complete ✓", run_id)

    except Exception as exc:
        log.exception("[%s] Pipeline failed: %s", run_id, exc)
        state.status = "error"
        state.error = str(exc)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/validate")
def start_validation(body: IdeaInput):
    """
    Step 1 — Submit the raw idea.
    Returns run_id + 4-5 clarifying questions to show in the UI.
    """
    run_id = str(uuid.uuid4())[:8]
    questions = get_clarifying_questions(body.idea)
    runs[run_id] = RunState(
        run_id=run_id,
        raw_idea=body.idea,
        status="awaiting_answers",
        questions=questions,
    )
    return {"run_id": run_id, "questions": questions}


@router.post("/answers/{run_id}")
def submit_answers(run_id: str, body: AnswerInput):
    """
    Step 2 — Submit answers to the clarifying questions.
    Builds the Idea Brief and kicks off the full pipeline in a background thread.
    """
    state = runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    state.answers = body.answers
    state.idea_brief = build_idea_brief(state.raw_idea, state.questions, body.answers)
    threading.Thread(target=_pipeline, args=(run_id,), daemon=True).start()
    return {"status": "pipeline_started", "run_id": run_id}


@router.get("/status/{run_id}")
def get_status(run_id: str):
    """Poll this to track the pipeline stage. Streamlit polls every 4 seconds."""
    state = runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "status": state.status, "error": state.error}


@router.get("/report/{run_id}")
def get_report(run_id: str):
    """Fetch the final ValidationReport once status == 'done'."""
    state = runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    if state.status != "done":
        raise HTTPException(status_code=202, detail=f"Not ready yet: {state.status}")
    return state.report
