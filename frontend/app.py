import time
import httpx
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(
    page_title="IdeaValidator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("screen", "input"),
    ("run_id", None),
    ("questions", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

PIPELINE_STAGES = [
    ("querying",        "Generating search queries",        "🧠"),
    ("scraping_reddit", "Scraping Reddit posts & comments", "🔍"),
    ("analyzing",       "AI analyzing the data",            "⚡"),
    ("done",            "Report ready",                     "✅"),
]
STAGE_KEYS = [s[0] for s in PIPELINE_STAGES]


# ── API helpers ───────────────────────────────────────────────────────────────

def api_post(path: str, payload: dict) -> dict | None:
    try:
        resp = httpx.post(f"{API}{path}", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        st.error("Cannot connect to the API. Make sure FastAPI is running on port 8000.")
    except Exception as exc:
        st.error(f"API error: {exc}")
    return None


def api_get(path: str) -> dict | None:
    try:
        resp = httpx.get(f"{API}{path}", timeout=15)
        if resp.status_code in (200, 202):
            return resp.json()
        if resp.status_code == 404:
            return {"_not_found": True}
    except httpx.ConnectError:
        st.error("Cannot connect to the API. Make sure FastAPI is running on port 8000.")
    except Exception as exc:
        st.error(f"API error: {exc}")
    return None


# ── Screen 1: Idea Input ──────────────────────────────────────────────────────

def screen_input():
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.title("🔍 IdeaValidator")
        st.markdown("##### Validate your startup idea with real data from Reddit")
        st.markdown("---")

        idea = st.text_area(
            "Describe your idea",
            placeholder=(
                "e.g. An app that helps remote workers find co-working "
                "buddies near them based on work schedule and interests..."
            ),
            height=160,
        )

        if st.button("Validate My Idea →", type="primary", use_container_width=True):
            if not idea.strip():
                st.warning("Please describe your idea first.")
                return
            with st.spinner("Analyzing your idea..."):
                result = api_post("/validate", {"idea": idea.strip()})
            if result:
                st.session_state.run_id = result["run_id"]
                st.session_state.questions = result["questions"]
                st.session_state.screen = "questions"
                st.rerun()

    with col_right:
        st.markdown("")
        st.markdown("")
        st.markdown("**What you'll get:**")
        st.markdown("""
🔥 **Buzz Score** — how much people are talking  
✅ **Validation Score** — how strong the demand is  
📊 **Sentiment breakdown**  
📈 **Key metrics** from scraped data  
✅ **Pros** backed by real posts  
⚠️ **Cons** backed by real posts  
💬 **Real quotes** from the community  
🧠 **AI reasoning** paragraph
        """)
        st.markdown("---")
        st.markdown("*No Reddit account needed. No YouTube key needed yet.*")


# ── Screen 2: Clarifying Questions ────────────────────────────────────────────

def screen_questions():
    st.title("🎯 A few quick questions")
    st.markdown(
        "The AI needs a bit more context to run better, more targeted research. "
        "Takes 30 seconds."
    )
    st.markdown("---")

    questions = st.session_state.questions
    answers = []
    for i, q in enumerate(questions):
        ans = st.text_input(f"**{i + 1}.** {q}", key=f"ans_{i}", placeholder="Your answer...")
        answers.append(ans.strip())

    st.markdown("")
    col_back, col_submit = st.columns([1, 5])
    with col_back:
        if st.button("← Back"):
            st.session_state.screen = "input"
            st.rerun()
    with col_submit:
        if st.button("Start Research →", type="primary"):
            if not all(answers):
                st.warning("Please answer all questions before continuing.")
                return
            with st.spinner("Building your idea profile and kicking off research..."):
                result = api_post(
                    f"/answers/{st.session_state.run_id}",
                    {"answers": answers},
                )
            if result:
                st.session_state.screen = "status"
                st.rerun()


# ── Screen 3: Pipeline Status ─────────────────────────────────────────────────

def screen_status():
    run_id = st.session_state.run_id
    data = api_get(f"/status/{run_id}")
    if not data:
        return

    # Server was restarted — run_id lost from memory
    if data.get("_not_found"):
        st.warning("The server was restarted and lost your session. Please start over.")
        if st.button("Start Over"):
            st.session_state.run_id = None
            st.session_state.questions = []
            st.session_state.screen = "input"
            st.rerun()
        return

    status = data.get("status", "unknown")

    st.title("🔬 Research in Progress")
    st.markdown(f"Run ID: `{run_id}`")
    st.markdown("---")

    current_idx = STAGE_KEYS.index(status) if status in STAGE_KEYS else -1

    for i, (key, label, icon) in enumerate(PIPELINE_STAGES):
        if i < current_idx:
            st.success(f"{icon} {label} — done")
        elif i == current_idx:
            st.info(f"{icon} **{label}** — in progress...")
        else:
            st.markdown(f"⬜ {label}")

    if status == "done":
        st.balloons()
        time.sleep(1)
        st.session_state.screen = "report"
        st.rerun()
    elif status == "error":
        st.error(f"Pipeline error: {data.get('error', 'Unknown error')}")
        if st.button("Start Over"):
            st.session_state.screen = "input"
            st.rerun()
    else:
        time.sleep(4)
        st.rerun()


# ── Screen 4: Report ──────────────────────────────────────────────────────────

def screen_report():
    run_id = st.session_state.run_id
    data = api_get(f"/report/{run_id}")
    if not data:
        st.error("Could not load the report.")
        return

    st.title("📊 Validation Report")
    st.markdown(f"Run ID: `{run_id}`")
    st.markdown("---")

    # ── Scores ────────────────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("🔥 Buzz Score", f"{data['buzz_score']} / 100")
    s2.metric("✅ Validation Score", f"{data['validation_score']} / 100")
    sent = data["sentiment"]
    s3.metric("😊 Positive", f"{sent['positive']}%")
    s4.metric("😟 Negative", f"{sent['negative']}%")

    st.markdown("---")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.subheader("📈 Data Collected")
    kpis = data["kpis"]
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Posts Scraped", kpis["total_posts"])
    k2.metric("Comments", kpis["total_comments"])
    k3.metric("Avg Upvotes", kpis["avg_upvotes"])
    k4.metric("Avg Pain Score", kpis["avg_pain_score"])
    k5.metric("Feature Requests", kpis["feature_request_count"])
    k6.metric("Subreddits", kpis["subreddits_found"])

    st.markdown("---")

    # ── Pros / Cons ───────────────────────────────────────────────────────────
    col_pros, col_cons = st.columns(2)
    with col_pros:
        st.subheader("✅ Pros")
        for item in data["pros"]:
            st.success(f"• {item}")
    with col_cons:
        st.subheader("⚠️ Cons")
        for item in data["cons"]:
            st.error(f"• {item}")

    st.markdown("---")

    # ── Key Quotes ────────────────────────────────────────────────────────────
    st.subheader("💬 Real Quotes from the Community")
    for quote in data["key_quotes"]:
        st.markdown(f"> *\"{quote}\"*")

    st.markdown("---")

    # ── AI Reasoning ─────────────────────────────────────────────────────────
    st.subheader("🧠 AI Analysis & Reasoning")
    st.info(data["reasoning"])

    st.markdown("---")
    if st.button("🔄 Validate Another Idea"):
        st.session_state.run_id = None
        st.session_state.questions = []
        st.session_state.screen = "input"
        st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────

screen = st.session_state.screen
if screen == "input":
    screen_input()
elif screen == "questions":
    screen_questions()
elif screen == "status":
    screen_status()
elif screen == "report":
    screen_report()
