"""
Reddit scraper — no API key required.
Uses Reddit's public JSON endpoints with a browser User-Agent.

Endpoints used:
  Search  : https://www.reddit.com/search.json?q={query}&sort=relevance&limit=100
  Comments: https://www.reddit.com/r/{sub}/comments/{id}.json?limit=100&sort=top

Pagination: uses the 'after' token to fetch multiple pages per query.

Future replacement: swap internals with PRAW (pip install praw) for official
API access and higher rate limits. Function signatures stay identical.
"""

import time
import logging
import httpx
from backend.config import REDDIT_HEADERS

log = logging.getLogger("reddit_scraper")

# ── Tuneable limits ───────────────────────────────────────────────────────────

MAX_POSTS_PER_QUERY   = 100   # posts fetched per search query (1 page = max 100)
MAX_PAGES_PER_QUERY   = 2     # pages of pagination per query  → up to 200 posts/query
MAX_COMMENT_POSTS     = 100   # fetch comments for the top N posts by score
MAX_COMMENTS_PER_POST = 100   # comments fetched per post

# ── Rule-based analysis word lists ───────────────────────────────────────────

PAIN_WORDS = {
    "struggle", "problem", "frustrated", "overwhelmed", "burnout",
    "hate", "broken", "annoying", "confusing", "difficult",
    "impossible", "failing", "lost", "stuck", "waste",
    "expensive", "slow", "buggy", "unreliable", "stressful",
    "painful", "exhausting", "tedious", "complicated", "awful",
    "terrible", "useless", "missing", "wish", "bad",
    "hard", "need",
}

FEATURE_PHRASES = [
    "is there an app",
    "wish there was",
    "best way to",
    "anyone know how to",
    "looking for a tool",
    "does anyone have",
    "i need something that",
    "why isn't there",
    "someone should make",
    "would love a",
    "is there a way",
    "any recommendations",
    "i want something",
    "build an app",
    "need a solution",
]

POSITIVE_WORDS = {
    "good", "great", "love", "amazing", "helpful", "excellent",
    "awesome", "best", "wonderful", "fantastic", "perfect",
    "brilliant", "outstanding", "superb", "useful", "recommend",
    "easy", "simple", "fast", "efficient", "effective",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "horrible", "worst", "hate",
    "useless", "broken", "poor", "disappointing", "frustrating",
    "annoying", "difficult", "complicated", "boring", "confusing",
    "slow", "buggy", "unreliable", "expensive",
}


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None, retries: int = 2) -> dict | list | None:
    for attempt in range(retries + 1):
        try:
            resp = httpx.get(url, params=params, headers=REDDIT_HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = 6 * (attempt + 1)
                log.warning("Rate limited — sleeping %ds", wait)
                time.sleep(wait)
            else:
                time.sleep(1)
        except Exception as exc:
            log.warning("HTTP error: %s", exc)
            time.sleep(2)
    return None


# ── Rule-based post analysis ──────────────────────────────────────────────────

def _analyze_post(title: str, body: str) -> dict:
    text = (title + " " + body).lower()
    words = set(text.split())

    pain_score = len(words & PAIN_WORDS)

    feature_flag = ""
    for phrase in FEATURE_PHRASES:
        if phrase in text:
            feature_flag = phrase
            break

    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    sentiment = "positive" if pos > neg else ("negative" if neg > pos else "neutral")

    return {
        "pain_score": pain_score,
        "feature_request_flag": feature_flag,
        "sentiment": sentiment,
    }


# ── Core scraping functions ───────────────────────────────────────────────────

def search_posts(query: str, max_posts: int = MAX_POSTS_PER_QUERY) -> list[dict]:
    """Single-page Reddit search — up to 100 results."""
    data = _get(
        "https://www.reddit.com/search.json",
        params={"q": query, "sort": "relevance", "limit": min(max_posts, 100), "type": "link"},
    )
    if not data:
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        p = child.get("data", {})
        posts.append({
            "post_id":      p.get("id", ""),
            "subreddit":    p.get("subreddit", ""),
            "title":        p.get("title", ""),
            "body":         p.get("selftext", ""),
            "score":        p.get("score", 0),
            "upvote_ratio": p.get("upvote_ratio", 0.0),
            "num_comments": p.get("num_comments", 0),
            "url":          p.get("url", ""),
            "permalink":    p.get("permalink", ""),
            "created_utc":  p.get("created_utc", 0),
        })
    time.sleep(0.5)
    return posts


def search_posts_paginated(
    query: str,
    max_posts: int = MAX_POSTS_PER_QUERY * MAX_PAGES_PER_QUERY,
) -> list[dict]:
    """Multi-page Reddit search using 'after' pagination token."""
    posts: list[dict] = []
    after: str | None = None
    pages_fetched = 0

    while len(posts) < max_posts and pages_fetched < MAX_PAGES_PER_QUERY:
        params: dict = {
            "q": query,
            "sort": "relevance",
            "limit": 100,
            "type": "link",
        }
        if after:
            params["after"] = after

        data = _get("https://www.reddit.com/search.json", params=params)
        if not data:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for child in children:
            p = child.get("data", {})
            posts.append({
                "post_id":      p.get("id", ""),
                "subreddit":    p.get("subreddit", ""),
                "title":        p.get("title", ""),
                "body":         p.get("selftext", ""),
                "score":        p.get("score", 0),
                "upvote_ratio": p.get("upvote_ratio", 0.0),
                "num_comments": p.get("num_comments", 0),
                "url":          p.get("url", ""),
                "permalink":    p.get("permalink", ""),
                "created_utc":  p.get("created_utc", 0),
            })

        after = data.get("data", {}).get("after")
        pages_fetched += 1
        if not after:
            break
        time.sleep(0.6)

    return posts[:max_posts]


def get_post_with_comments(
    subreddit: str,
    post_id: str,
    limit: int = MAX_COMMENTS_PER_POST,
) -> list[dict]:
    """Fetch top comments for a single post."""
    data = _get(
        f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json",
        params={"limit": limit, "sort": "top"},
    )
    if not data or not isinstance(data, list) or len(data) < 2:
        return []

    comments = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child.get("data", {})
        body = c.get("body", "")
        if not body or body in ("[deleted]", "[removed]"):
            continue
        comments.append({
            "post_id":    post_id,
            "comment_id": c.get("id", ""),
            "body":       body,
            "score":      c.get("score", 0),
            "created_utc": c.get("created_utc", 0),
        })
    time.sleep(0.3)
    return comments


# ── Main entry point ──────────────────────────────────────────────────────────

def run_all_queries(run_id: str, queries: list[str]) -> tuple[list[dict], list[dict]]:
    """
    Run all search queries with pagination, deduplicate by post_id,
    fetch comments for the top MAX_COMMENT_POSTS posts, and run
    rule-based analysis on every post.

    Returns:
        posts    — all unique posts with rule-based analysis fields
        comments — all comments from top posts
    """
    seen_ids: set[str] = set()
    all_posts: list[dict] = []

    for i, query in enumerate(queries):
        log.info("[%s] Query %d/%d: %s", run_id, i + 1, len(queries), query)
        for post in search_posts_paginated(query):
            pid = post["post_id"]
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                post["query"] = query
                post["run_id"] = run_id
                post.update(_analyze_post(post["title"], post["body"]))
                all_posts.append(post)

    log.info("[%s] Unique posts after dedup: %d", run_id, len(all_posts))

    # Sort by score, fetch comments for top posts
    all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    top_posts = all_posts[:MAX_COMMENT_POSTS]

    all_comments: list[dict] = []
    for j, post in enumerate(top_posts):
        sub = post.get("subreddit", "")
        pid = post.get("post_id", "")
        if sub and pid:
            comments = get_post_with_comments(sub, pid)
            for c in comments:
                c["run_id"] = run_id
                all_comments.append(c)
            if (j + 1) % 10 == 0:
                log.info("[%s] Comments fetched for %d/%d posts", run_id, j + 1, len(top_posts))

    log.info("[%s] Total comments collected: %d", run_id, len(all_comments))
    return all_posts, all_comments
