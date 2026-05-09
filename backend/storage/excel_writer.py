import pandas as pd
from backend.config import DATA_DIR


def save_run(
    run_id: str,
    reddit_posts: list[dict],
    reddit_comments: list[dict],
    youtube_videos: list[dict] | None = None,
    youtube_comments: list[dict] | None = None,
) -> str:
    """
    Save all scraped data into a single Excel file with 4 sheets.
    YouTube sheets are created empty now and will be populated once
    the YouTube scraper is wired in.

    Returns the file path as a string.
    """
    path = DATA_DIR / f"{run_id}.xlsx"

    with pd.ExcelWriter(str(path), engine="openpyxl") as writer:
        pd.DataFrame(reddit_posts).to_excel(writer, sheet_name="reddit_posts", index=False)
        pd.DataFrame(reddit_comments).to_excel(writer, sheet_name="reddit_comments", index=False)
        pd.DataFrame(youtube_videos or []).to_excel(writer, sheet_name="youtube_videos", index=False)
        pd.DataFrame(youtube_comments or []).to_excel(writer, sheet_name="youtube_comments", index=False)

    return str(path)
