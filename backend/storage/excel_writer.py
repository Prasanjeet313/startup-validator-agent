import re
import pandas as pd
from backend.config import DATA_DIR

# Excel (openpyxl) rejects control characters outside the allowed set
# (tab 0x09, newline 0x0A, carriage return 0x0D). Strip them silently.
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Remove Excel-illegal characters from every string cell."""
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda x: _ILLEGAL.sub("", x) if isinstance(x, str) else x
            )
    return df


def save_run(
    run_id: str,
    reddit_posts: list[dict],
    reddit_comments: list[dict],
    youtube_videos: list[dict] | None = None,
    youtube_comments: list[dict] | None = None,
) -> str:
    """
    Save all scraped data into a single Excel file with 4 sheets.
    Returns the file path as a string.
    """
    path = DATA_DIR / f"{run_id}.xlsx"

    with pd.ExcelWriter(str(path), engine="openpyxl") as writer:
        _clean(pd.DataFrame(reddit_posts)).to_excel(
            writer, sheet_name="reddit_posts", index=False
        )
        _clean(pd.DataFrame(reddit_comments)).to_excel(
            writer, sheet_name="reddit_comments", index=False
        )
        _clean(pd.DataFrame(youtube_videos or [])).to_excel(
            writer, sheet_name="youtube_videos", index=False
        )
        _clean(pd.DataFrame(youtube_comments or [])).to_excel(
            writer, sheet_name="youtube_comments", index=False
        )

    return str(path)
