# IdeaValidator — Product Plan

## Vision

A research platform where anyone can submit a raw idea and receive a full automated validation report.
The platform crawls social platforms, extracts real-world sentiment and buzz, and produces structured market intelligence — so founders, product managers, and indie hackers can validate ideas before building anything.

---

## Core User Flow

```
User submits idea (text prompt)
        ↓
Backend kicks off research pipeline
        ↓
┌─────────────────────────────────────────────────────┐
│  Reddit  │  YouTube  │  Facebook / Insta  │  News   │
└─────────────────────────────────────────────────────┘
        ↓
Sentiment analysis + buzz scoring
        ↓
Market sizing (TAM / SAM / SOM)
        ↓
SWOT analysis generation
        ↓
Final validation report rendered to user
```

---

## Tech Stack


| Layer      | Choice                                            | Reason                                      |
| ---------- | ------------------------------------------------- | ------------------------------------------- |
| Frontend   | Streamlit                                         | Fast to demo, no frontend build overhead    |
| Backend    | FastAPI                                           | Async-friendly, easy to structure pipelines |
| AI / LLM   | OpenAI / Groq                                     | Summarisation, SWOT, sentiment reasoning    |
| Scraping   | PRAW (Reddit), YouTube Data API, Apify (Insta/FB) | Per-platform best tools                     |
| Storage    | SQLite (MVP) → PostgreSQL (scale)                 | Store reports, cache results                |
| Task Queue | Celery + Redis (phase 2)                          | For async long-running research jobs        |


---

## Feature Breakdown

### Phase 1 — MVP (Reddit + YouTube only)

- Idea submission form (Streamlit)
- Reddit research module
  - Search top posts and comments by keyword
  - Sentiment scoring (positive / negative / neutral %)
  - Buzz score (post count, upvote velocity, comment volume)
  - Extract top recurring themes / pain points
- YouTube research module
  - Search videos by keyword
  - Scrape top comments
  - Sentiment analysis on comments
  - View count + engagement as proxy for interest level
- Report generation
  - Summary of findings per platform
  - Overall hype score (0–100)
  - Key quotes / excerpts from real users
- FastAPI backend exposing `/validate` endpoint
- Streamlit frontend consuming the API and rendering the report

### Phase 2 — Extended Social Coverage

- Facebook Groups research (via Apify or Meta Graph API)
- Instagram hashtag and post comment analysis
- Twitter / X keyword and hashtag sentiment
- Aggregate cross-platform buzz score

### Phase 3 — Market Intelligence Layer

- TAM / SAM / SOM estimation using web data + LLM reasoning
- SWOT analysis auto-generation (LLM-powered)
- Competitor detection (who is already solving this?)
- Trend graph (is the buzz growing or dying?)
- Related keyword suggestions

### Phase 4 — Product Polish

- User accounts and saved reports
- Report export (PDF / Notion)
- Shareable report links
- Email report delivery
- Webhook / API access for power users

---

## Backend Architecture (FastAPI)

```
/api
  /validate          POST  — submit idea, trigger full pipeline
  /report/{id}       GET   — fetch completed report
  /status/{id}       GET   — check pipeline progress

/services
  reddit_service.py       — PRAW integration, search + sentiment
  youtube_service.py      — YouTube Data API, comment scraping
  instagram_service.py    — Apify / scraper integration
  facebook_service.py     — Apify / Graph API integration
  sentiment_service.py    — Shared sentiment scoring logic
  market_service.py       — TAM/SAM/SOM estimation, SWOT generation
  report_service.py       — Aggregates all signals into final report

/models
  idea.py                 — Idea schema
  report.py               — Report schema
  platform_result.py      — Per-platform result schema
```

---

## Frontend Architecture (Streamlit)

```
pages/
  1_Submit_Idea.py        — Idea input form
  2_Research_Status.py    — Live progress tracker
  3_Report.py             — Full report viewer

components/
  sentiment_chart.py      — Pie / bar chart for sentiment breakdown
  buzz_meter.py           — Hype score gauge
  quote_card.py           — Real user quote cards
  swot_table.py           — SWOT matrix display
  market_size_card.py     — TAM/SAM/SOM display
```

---

## Report Structure (What the User Sees)

```
Idea: "An app to find study partners near you"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Overall Hype Score:  74 / 100  🔥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Platform Breakdown
  Reddit    — 68% positive  |  320 relevant posts  |  Buzz: High
  YouTube   — 74% positive  |  85 videos  |  Avg views: 42k

Top Themes People Are Talking About
  - Difficulty finding reliable study partners
  - Preference for same-subject pairing
  - Safety concerns in meetups

Real Quotes from the Community
  "I wish there was a Tinder but for study buddies..."
  "Been looking for a CS study group for months..."

Market Size Estimate
  TAM: $4.2B  |  SAM: $800M  |  SOM: $40M

SWOT Analysis
  Strengths : Strong community demand, low existing competition
  Weaknesses: Safety and trust challenges, retention risk
  Opportunities: University partnerships, gamification
  Threats: Existing social platforms adding similar features

Competitors Detected
  - Studystream, Focusmate, Discord study servers
```

---

## Data Sources & APIs


| Platform  | Method                     | Free Tier?        |
| --------- | -------------------------- | ----------------- |
| Reddit    | PRAW (official API)        | Yes               |
| YouTube   | YouTube Data API v3        | Yes (quota limit) |
| Instagram | Apify scraper / unofficial | Paid              |
| Facebook  | Apify scraper / Graph API  | Limited           |
| Twitter/X | X API Basic                | Limited free      |
| News      | NewsAPI / Google News RSS  | Yes               |


---

## Milestones


| Milestone | Deliverable                                 | Target   |
| --------- | ------------------------------------------- | -------- |
| M1        | FastAPI skeleton + Reddit service working   | Week 1   |
| M2        | YouTube service + basic report output       | Week 2   |
| M3        | Streamlit UI connected to API, demo-ready   | Week 3   |
| M4        | SWOT + market size via LLM                  | Week 4   |
| M5        | Instagram / Facebook integration            | Week 5–6 |
| M6        | Polished report UI, export, shareable links | Week 7–8 |


---

## Open Questions / Decisions Needed

- Which LLM provider for SWOT + summarisation? (OpenAI vs Groq vs local)
- Rate limiting strategy for free API tiers during demos
- Do we cache reports to avoid re-running the same idea twice?
- Authentication in MVP or skip until Phase 4?
- Deployment target for demo (Streamlit Cloud, Railway, Render?)

