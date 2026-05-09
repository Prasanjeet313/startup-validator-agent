# Phase 1 — TODO & Build Plan

## IdeaValidator MVP (Reddit + YouTube | Multi-Agent Pipeline)

---

## Tech Stack (Locked for Phase 1)


| Layer            | Tool / Library                   | Purpose                                            |
| ---------------- | -------------------------------- | -------------------------------------------------- |
| Language         | Python 3.11+                     | Everything                                         |
| Env Manager      | `uv`                             | Fast venv creation and package installs            |
| Backend          | FastAPI                          | API server, orchestrates the agent pipeline        |
| Frontend         | Streamlit                        | UI for idea input, live status, and final report   |
| LLM              | OpenAI GPT-4o (via `openai` SDK) | All 3 agents — clarification, query gen, analysis  |
| Reddit Scraping  | Direct JSON (no API key)         | Hit Reddit's public `.json` endpoints with `httpx` |
| YouTube Scraping | `google-api-python-client`       | YouTube Data API v3 — videos + comments            |
| Data Storage     | `pandas` + `openpyxl`            | Save all scraped data into Excel per run           |
| HTTP Client      | `httpx`                          | Async requests between Streamlit and FastAPI       |
| Config           | `python-dotenv`                  | Load OPENAI_API_KEY from `.env`                    |
| Unique IDs       | `uuid`                           | Track each validation run                          |


---

## Project Folder Structure

```
learnings/
├── .env                        ← OPENAI_API_KEY lives here (already done)
├── plan.md
├── todo.md                     ← this file
├── pyproject.toml              ← uv project config + dependencies
│
├── backend/
│   ├── main.py                 ← FastAPI app entry point
│   ├── routers/
│   │   └── validate.py         ← POST /validate  |  GET /report/{id}  |  GET /status/{id}
│   │
│   ├── agents/
│   │   ├── clarification_agent.py   ← Agent 1: asks 4-5 clarifying questions
│   │   ├── query_agent.py           ← Agent 2: generates Reddit + YouTube search queries
│   │   └── analysis_agent.py        ← Agent 3: analyzes all data, produces scores + report
│   │
│   ├── scrapers/
│   │   ├── reddit_scraper.py        ← No-key JSON scraper: search + top posts + comments + pre-analysis
│   │   └── youtube_scraper.py       ← YouTube API: search videos, fetch top comments
│   │
│   ├── storage/
│   │   └── excel_writer.py          ← Saves all scraped data into .xlsx per run
│   │
│   ├── models/
│   │   ├── idea.py                  ← Pydantic: IdeaInput, ClarifiedIdea
│   │   └── report.py                ← Pydantic: ValidationReport, PlatformResult
│   │
│   └── config.py                    ← Loads .env, sets constants
│
├── frontend/
│   └── app.py                  ← Streamlit single-page app
│
└── data/
    └── runs/                   ← Excel files saved here, one per run
        └── {run_id}.xlsx
```

---

## End-to-End Pipeline (How Everything Moves)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1 — User enters raw idea in Streamlit                             │
│  e.g. "An app to find study partners near me"                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  POST /validate  { "idea": "..." }
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2 — Agent 1: Clarification Agent  (GPT-4o)                        │
│                                                                         │
│  • Reads the raw idea                                                   │
│  • Decides if it needs more context                                     │
│  • Returns 4–5 targeted clarifying questions                            │
│  • Streamlit shows the questions to the user                            │
│  • User answers them in the UI                                          │
│  • Answers + original idea sent back → Agent 1 synthesises a           │
│    structured "Idea Brief" (target user, problem, geography, etc.)      │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  Idea Brief (structured JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3 — Agent 2: Query Generator Agent  (GPT-4o)                      │
│                                                                         │
│  • Takes the Idea Brief                                                 │
│  • Generates 5–8 optimised Reddit search queries                        │
│  • Generates 5–8 optimised YouTube search queries                       │
│  • Returns a query plan JSON                                            │
│  e.g. Reddit: ["study partner app", "finding study buddies reddit", …]  │
│       YouTube: ["study with me app review", "find study partners", …]   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  Query Plan
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4 — Scraping Pipeline                                             │
│                                                                         │
│  Reddit (No API key — public JSON endpoints)                            │
│    • Global search: reddit.com/search.json?q={query}&sort=relevance     │
│      &limit=50&type=link  →  fetch up to 50 posts per query            │
│    • Top 50 posts by score → fetch full post + comments:               │
│      reddit.com/r/{sub}/comments/{id}.json?limit=50                    │
│    • Fallback: old.reddit.com HTML parsing if JSON returns empty        │
│    • Deduplication by post_id across all queries                        │
│    • Pre-analysis on every post (rule-based, before LLM):              │
│        Pain Score       — count hits from 32 pain words in title+body  │
│        Feature Flag     — check 15 "wish there was / is there an app"  │
│                           phrases, save matched phrase                  │
│        Sentiment        — count positive vs negative word hits →        │
│                           returns positive / negative / neutral         │
│    • Capture: title, body, score, upvote_ratio, num_comments, subreddit │
│               pain_score, feature_request_flag, sentiment, url          │
│               comment text, comment score, comment date                 │
│                                                                         │
│  YouTube (Data API v3)                                                  │
│    • For each query: search top 10 videos                               │
│    • Per video: fetch top 30 comments                                   │
│    • Capture: title, description, view_count, like_count, comment_count │
│               comment text, comment likes, published_at                 │
│                                                                         │
│  All data → saved to data/runs/{run_id}.xlsx                            │
│    Sheet 1: reddit_posts                                                │
│    Sheet 2: reddit_comments                                             │
│    Sheet 3: youtube_videos                                              │
│    Sheet 4: youtube_comments                                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  Excel file path
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5 — Agent 3: Analysis Agent  (GPT-4o)                             │
│                                                                         │
│  • Reads all Reddit + YouTube data from Excel                           │
│  • Thinks through and produces:                                         │
│                                                                         │
│    Buzz Score       0–100  (how much people are talking about this)     │
│    Validation Score 0–100  (how much real demand / pain exists)         │
│                                                                         │
│    Sentiment        % Positive / Neutral / Negative                     │
│                                                                         │
│    KPIs             Total posts scanned, total comments, avg upvotes,   │
│                     avg engagement, subreddits active in, etc.          │
│                                                                         │
│    Pros             What people love / what pain they feel              │
│    Cons             Objections, risks, doubts raised                    │
│                                                                         │
│    Key Quotes       5–10 real verbatim quotes from users                │
│                                                                         │
│    Reasoning        A full paragraph: why this score, what the data     │
│                     says, what the agent concluded — backed by numbers  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │  ValidationReport JSON
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 6 — Streamlit renders the final report                            │
│                                                                         │
│  • Buzz Score gauge + Validation Score gauge                            │
│  • Sentiment pie chart                                                  │
│  • KPI metric cards                                                     │
│  • Pros / Cons side-by-side                                             │
│  • Real quotes block                                                    │
│  • Agent reasoning paragraph                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## TODO Checklist (Build Order)

### 0. Environment Setup

- `0.1` Create virtual env → `uv venv .venv`
- `0.2` Activate venv → `.venv\Scripts\activate`
- `0.3` Install all packages → `uv pip install -r requirements.txt`
- `0.4` Verify `.env` is loaded correctly (OPENAI_API_KEY check)
- `0.5` *(Deferred)* Create YouTube Data API v3 key → add `YOUTUBE_API_KEY` to `.env`

> **No Reddit credentials needed** — using public JSON endpoints.
> **No YouTube key needed right now** — scraper code exists but pipeline skips it until key is added.

### 1. Project Skeleton

- `1.1` Create folder structure (`backend/`, `frontend/`, `data/runs/`)
- `1.2` `backend/config.py` — load all env vars, set defaults
- `1.3` `backend/models/idea.py` — Pydantic schemas for idea input + clarified idea
- `1.4` `backend/models/report.py` — Pydantic schemas for final report + platform result
- `1.5` `backend/main.py` — FastAPI app with CORS, health check `/ping`

### 2. Agent 1 — Clarification Agent

- `2.1` `agents/clarification_agent.py`
  - Input: raw idea string
  - System prompt: you are an idea analyst. Ask sharp, targeted questions.
  - Output 1: list of 4–5 clarifying questions (JSON)
  - Output 2 (after answers received): structured Idea Brief (JSON)
- `2.2` Define the Idea Brief schema:
  ```
  {
    "core_idea": str,
    "target_user": str,
    "problem_being_solved": str,
    "geography": str,
    "unique_angle": str,
    "keywords": [str]
  }
  ```
- `2.3` Unit test: feed a sample idea → check questions come back → feed answers → check Idea Brief comes back

### 3. Agent 2 — Query Generator Agent

- `3.1` `agents/query_agent.py`
  - Input: Idea Brief JSON
  - System prompt: you are a research strategist. Generate queries that surface real user pain, demand, and discussion.
  - Output: query plan JSON
  ```
  {
    "reddit_queries": ["...", "...", ...],   // 5–8 queries
    "youtube_queries": ["...", "...", ...]   // 5–8 queries
  }
  ```
- `3.2` Unit test: feed a sample Idea Brief → validate query plan format

### 4. Reddit Scraper  *(no API key required)*

> **Future replacement:** swap this module with PRAW (`pip install praw`) when/if
> you want official API access, higher rate limits, or OAuth. The output schema
> of every function stays identical so the rest of the pipeline needs zero changes.

- `4.1` `scrapers/reddit_scraper.py` — HTTP client setup
  - Use `httpx` with a realistic browser `User-Agent` header (required or Reddit blocks)
  - No credentials needed, no `.env` changes
- `4.2` `search_posts(query, limit=50)` function
  - Hits `https://www.reddit.com/search.json?q={query}&sort=relevance&limit=50&type=link`
  - Returns list of raw post dicts
- `4.3` `get_post_with_comments(subreddit, post_id, limit=50)` function
  - Hits `https://www.reddit.com/r/{sub}/comments/{id}.json?limit=50`
  - Returns post body + list of top comments
  - Fallback: parse `https://old.reddit.com/r/{sub}/comments/{id}` HTML if JSON is empty
- `4.4` `analyze_post(title, body)` function — rule-based pre-analysis
  - **Pain score** — count occurrences of 32 pain words in title + body
  `(struggle, problem, frustrated, overwhelmed, burnout, hate, broken, annoying, confusing, difficult, impossible, failing, lost, stuck, waste, expensive, slow, buggy, unreliable, stressful, painful, exhausting, tedious, complicated, awful, terrible, useless, broken, missing, need, wish, help)`
  - **Feature request flag** — check if any of 15 phrases appear, save matched phrase
  `("is there an app", "wish there was", "best way to", "anyone know how to", "looking for a tool", "does anyone have", "i need something that", "why isn't there", "someone should make", "would love a", "is there a way", "any recommendations", "i want something", "build an app", "need a solution")`
  - **Sentiment** — count positive vs negative word hits → returns `positive / negative / neutral`
- `4.5` `run_all_queries(queries)` function
  - Loops all queries → calls `search_posts` for each
  - Deduplicates by `post_id` across all query results
  - For top 50 posts by score → calls `get_post_with_comments`
  - Calls `analyze_post` on every post
  - Returns combined `(posts_list, comments_list)`
- `4.6` Data captured per post:
`run_id, query, post_id, title, body, score, upvote_ratio, num_comments,`
`subreddit, url, created_utc, pain_score, feature_request_flag, sentiment`
- `4.7` Data captured per comment:
`run_id, post_id, comment_id, body, score, created_utc`
- `4.8` Unit test: run 1 query, confirm posts + comments come back, check pain_score and sentiment fields exist

### 5. YouTube Scraper  *(Phase 1 — code created, NOT wired into pipeline yet)*

> **Status:** `youtube_scraper.py` is written and lives in `scrapers/` but is **not imported
> or called** in `routers/validate.py`. A clear `# YouTube hook` comment marks exactly
> where to plug it in. Activate by:
>
> 1. Getting YouTube Data API v3 key (console.cloud.google.com)
> 2. Adding `YOUTUBE_API_KEY=...` to `.env`
> 3. Uncommenting the YouTube lines in `routers/validate.py`
> 4. Adding youtube sheets to `excel_writer.py` (already has empty sheet slots ready)

- `5.1` `scrapers/youtube_scraper.py` — written, all functions ready
- `5.2` Get YouTube Data API v3 key → add to `.env`
- `5.3` Uncomment YouTube hook in `routers/validate.py`
- `5.4` Unit test: run 1 query, confirm videos + comments come back, print sample

### 6. Excel Writer

- `6.1` `storage/excel_writer.py`
  - `save_run(run_id, reddit_posts, reddit_comments, youtube_videos, youtube_comments)`
  - Creates `data/runs/{run_id}.xlsx` with 4 sheets
  - Returns file path
- `6.2` Unit test: feed mock data → check Excel file created with correct sheets + row counts

### 7. Agent 3 — Analysis Agent

- `7.1` `agents/analysis_agent.py`
  - Input: Excel file path + Idea Brief
  - Reads all 4 sheets into text summaries (top N rows to stay within token limits)
  - System prompt: you are a market research analyst. You have real data from Reddit and YouTube. Be specific, cite numbers, quote real users.
  - Output: ValidationReport JSON
  ```
  {
    "buzz_score": int (0–100),
    "validation_score": int (0–100),
    "sentiment": { "positive": %, "neutral": %, "negative": % },
    "kpis": { "total_posts": int, "total_comments": int, "avg_upvotes": float, ... },
    "pros": [str, str, ...],
    "cons": [str, str, ...],
    "key_quotes": [str, str, ...],
    "reasoning": str
  }
  ```
- `7.2` Unit test: feed sample Excel + Idea Brief → validate report structure

### 8. FastAPI Router — Validate

- `8.1` `routers/validate.py`
  - `POST /validate` — accepts raw idea, starts pipeline, returns `run_id`
  - `GET /status/{run_id}` — returns current stage (clarifying / querying / scraping / analyzing / done)
  - `GET /questions/{run_id}` — returns clarifying questions to show in UI
  - `POST /answers/{run_id}` — accepts user answers, continues pipeline
  - `GET /report/{run_id}` — returns final ValidationReport JSON
- `8.2` Wire all agents + scrapers + Excel writer inside the pipeline function
- `8.3` Add basic in-memory run state tracking (dict keyed by run_id)

### 9. Streamlit Frontend

- `9.1` `frontend/app.py` — single page, session-state driven
- `9.2` Screen 1 — Idea Input
  - Text area for raw idea
  - Submit button → calls `POST /validate`
- `9.3` Screen 2 — Clarifying Questions
  - Renders the 4–5 questions as labeled text inputs
  - Submit answers → calls `POST /answers/{run_id}`
- `9.4` Screen 3 — Processing Status
  - Polls `GET /status/{run_id}` every 3 seconds
  - Shows live stage: "Generating queries... → Scraping Reddit... → Analyzing..."
- `9.5` Screen 4 — Report
  - Buzz Score + Validation Score as big number cards
  - Sentiment bar (positive / neutral / negative %)
  - KPI metrics row
  - Pros (green) / Cons (red) two-column list
  - Key Quotes block (italics, bordered)
  - Agent Reasoning paragraph

### 10. End-to-End Test

- `10.1` Run FastAPI locally → `uvicorn backend.main:app --reload`
- `10.2` Run Streamlit → `streamlit run frontend/app.py`
- `10.3` Submit test idea: `"A mobile app to track your daily water intake"`
- `10.4` Answer the clarifying questions the agent returns
- `10.5` Watch pipeline run through all stages
- `10.6` Check `data/runs/{run_id}.xlsx` — verify all 4 sheets have data
- `10.7` Verify final report renders correctly in Streamlit

---

## API Keys Needed (Before You Can Build)


| Key             | Where to Get                                          | Add to .env as    |
| --------------- | ----------------------------------------------------- | ----------------- |
| OpenAI API Key  | Already done ✅                                        | `OPENAI_API_KEY`  |
| Reddit          | **No key needed** — public JSON endpoints ✅           | —                 |
| YouTube API Key | console.cloud.google.com → Enable YouTube Data API v3 | `YOUTUBE_API_KEY` |


> **Future (Reddit official API):** when ready to upgrade, create an app at
> reddit.com/prefs/apps (script type) and add `REDDIT_CLIENT_ID`,
> `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` to `.env`.
> Then swap `reddit_scraper.py` internals with PRAW — zero changes elsewhere.

---

## Dependencies (for pyproject.toml / requirements.txt)

```
fastapi
uvicorn[standard]
streamlit
openai
httpx                      # Reddit JSON scraping + async HTTP between services
google-api-python-client   # YouTube Data API v3
pandas
openpyxl
python-dotenv
pydantic
```

> **Future dependency:** add `praw` when switching Reddit scraper to official API.

---

## Testing Strategy


| What to Test        | How                                                                                      |
| ------------------- | ---------------------------------------------------------------------------------------- |
| Agent 1 (Clarifier) | Unit test with 3 sample ideas, check 4–5 questions returned                              |
| Agent 2 (Query Gen) | Unit test with 2 Idea Briefs, check valid JSON query plan                                |
| Reddit Scraper      | Live test with 1 query, print 5 posts + 10 comments, check pain_score / sentiment fields |
| YouTube Scraper     | Live test with 1 query, print 3 videos + 10 comments                                     |
| Excel Writer        | Feed mock data, open file, check sheets manually                                         |
| Agent 3 (Analyzer)  | Feed real Excel from scraper run, check all report fields exist                          |
| FastAPI endpoints   | Use `/docs` (Swagger UI) to hit each endpoint manually                                   |
| Full E2E            | Run Streamlit + FastAPI together, test 2–3 ideas end to end                              |


---

## Next Step When You're Ready

```
Step 0: Nothing to get — Reddit needs no key, YouTube is deferred
Step 1: uv venv .venv  →  activate  →  uv pip install -r requirements.txt  →  run both servers
```

