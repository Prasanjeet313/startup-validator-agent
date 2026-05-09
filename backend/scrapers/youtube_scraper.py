"""
YouTube scraper — Phase 1 (code ready, NOT wired into the pipeline yet).

To activate when you have a YouTube Data API v3 key:
  1. Go to console.cloud.google.com → create project → enable YouTube Data API v3
  2. Create an API Key → add YOUTUBE_API_KEY=<key> to .env
  3. In backend/routers/validate.py, find the comment marked "# YouTube hook"
     and uncomment the two lines there.

Future alternative: yt-dlp for comment scraping without quota limits.
"""

from googleapiclient.discovery import build
from backend.config import YOUTUBE_API_KEY


def _client():
    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY is not set in .env — YouTube scraping is not active yet."
        )
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_videos(query: str, limit: int = 10) -> list[dict]:
    """Search YouTube for videos matching the query."""
    yt = _client()
    resp = yt.search().list(
        q=query,
        part="snippet",
        maxResults=limit,
        type="video",
        order="relevance",
    ).execute()

    videos = []
    for item in resp.get("items", []):
        snippet = item["snippet"]
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        })
    return videos


def get_video_stats(video_ids: list[str]) -> dict[str, dict]:
    """Fetch view/like/comment counts for a list of video IDs."""
    yt = _client()
    resp = yt.videos().list(id=",".join(video_ids), part="statistics").execute()
    return {item["id"]: item.get("statistics", {}) for item in resp.get("items", [])}


def get_comments(video_id: str, limit: int = 30) -> list[dict]:
    """Fetch top-level comments for a video (returns [] if comments are disabled)."""
    yt = _client()
    try:
        resp = yt.commentThreads().list(
            videoId=video_id,
            part="snippet",
            maxResults=limit,
            order="relevance",
        ).execute()
    except Exception:
        return []

    comments = []
    for item in resp.get("items", []):
        top = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "video_id": video_id,
            "comment_id": item["id"],
            "text": top.get("textDisplay", ""),
            "like_count": top.get("likeCount", 0),
            "published_at": top.get("publishedAt", ""),
        })
    return comments


def run_all_queries(run_id: str, queries: list[str]) -> tuple[list[dict], list[dict]]:
    """
    Run all YouTube queries, deduplicate by video_id, enrich with stats,
    fetch comments for top 10 by view count.

    Returns:
        videos   — all unique videos with stats attached
        comments — all comments from top 10 videos
    """
    seen_ids: set[str] = set()
    all_videos: list[dict] = []

    for query in queries:
        for video in search_videos(query):
            vid = video["video_id"]
            if vid not in seen_ids:
                seen_ids.add(vid)
                video["query"] = query
                video["run_id"] = run_id
                all_videos.append(video)

    if all_videos:
        stats = get_video_stats([v["video_id"] for v in all_videos])
        for v in all_videos:
            s = stats.get(v["video_id"], {})
            v["view_count"] = int(s.get("viewCount", 0))
            v["like_count"] = int(s.get("likeCount", 0))
            v["comment_count"] = int(s.get("commentCount", 0))

    top_videos = sorted(all_videos, key=lambda v: v.get("view_count", 0), reverse=True)[:10]
    all_comments: list[dict] = []
    for v in top_videos:
        for c in get_comments(v["video_id"]):
            c["run_id"] = run_id
            all_comments.append(c)

    return all_videos, all_comments
