import time
import httpx
import streamlit as st
import plotly.graph_objects as go

API = "http://localhost:8000"

st.set_page_config(
    page_title="IdeaValidator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("screen", "input"),
    ("run_id", None),
    ("questions", []),
    ("provider", "groq"),
    ("model", "llama-3.3-70b-versatile"),
    ("api_key", ""),
    ("providers_data", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

PIPELINE_STAGES = [
    ("querying",        "Generating search queries",              "🧠"),
    ("scraping_reddit", "Scraping Reddit posts & comments",       "🔍"),
    ("searching_web",   "Searching web, Wikipedia & blogs",       "🌐"),
    ("analyzing",       "Running AI agents in parallel",          "⚡"),
    ("done",            "Report ready",                           "✅"),
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


def _llm_config() -> dict:
    return {
        "provider": st.session_state.provider,
        "model": st.session_state.model,
        "api_key": st.session_state.api_key if st.session_state.api_key else None,
    }


# ── Sidebar: Provider & Model Selection ──────────────────────────────────────

def sidebar_provider_settings():
    st.sidebar.title("⚙️ AI Provider")
    st.sidebar.markdown("---")

    if st.session_state.providers_data is None:
        data = api_get("/providers")
        if data:
            st.session_state.providers_data = data.get("providers", [])

    providers = st.session_state.providers_data or []
    if not providers:
        st.sidebar.warning("Could not load providers. Is the backend running?")
        return False

    provider_ids = [p["id"] for p in providers]
    provider_names = {p["id"]: p["name"] for p in providers}
    current_idx = provider_ids.index(st.session_state.provider) if st.session_state.provider in provider_ids else 0

    selected_provider_id = st.sidebar.selectbox(
        "Provider",
        options=provider_ids,
        format_func=lambda x: provider_names[x],
        index=current_idx,
        key="provider_select",
    )

    if selected_provider_id != st.session_state.provider:
        provider_info = next(p for p in providers if p["id"] == selected_provider_id)
        st.session_state.provider = selected_provider_id
        st.session_state.model = provider_info["default_model"]
        st.session_state.api_key = ""
        st.rerun()

    provider_info = next(p for p in providers if p["id"] == selected_provider_id)
    models = provider_info["models"]
    current_model = st.session_state.model
    model_idx = models.index(current_model) if current_model in models else 0

    st.session_state.model = st.sidebar.selectbox(
        "Model", options=models, index=model_idx, key="model_select"
    )

    st.sidebar.markdown("**API Key**")
    has_env_key = provider_info["has_env_key"]
    if has_env_key and not st.session_state.api_key:
        st.sidebar.caption("Using key from .env")

    api_key_input = st.sidebar.text_input(
        "API Key",
        value=st.session_state.api_key,
        placeholder="Override .env key..." if has_env_key else "Paste your API key here...",
        type="password",
        label_visibility="collapsed",
        key="api_key_input",
    )
    st.session_state.api_key = api_key_input

    key_ok = has_env_key or bool(api_key_input)
    if key_ok:
        st.sidebar.success(f"✅ {provider_names[selected_provider_id]} ready")
    else:
        st.sidebar.warning("⚠️ Enter an API key to continue")

    st.sidebar.markdown("---")
    st.sidebar.caption("Groq · Gemini · OpenAI · Anthropic · Ollama")
    return key_ok


# ── Plotly chart helpers ──────────────────────────────────────────────────────

def _gauge(value: int, title: str, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 16, "color": "#111827"}},
        number={"font": {"color": "#111827", "size": 36}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#111827",
                     "tickfont": {"color": "#111827"}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "white",
            "steps": [
                {"range": [0, 33],  "color": "#fee2e2"},
                {"range": [33, 66], "color": "#fef9c3"},
                {"range": [66, 100],"color": "#dcfce7"},
            ],
            "threshold": {
                "line": {"color": "#1e293b", "width": 3},
                "thickness": 0.75,
                "value": value,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="white",
        font=dict(color="#111827"),
    )
    return fig


def _sentiment_donut(sent: dict) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["Positive", "Neutral", "Negative"],
        values=[sent["positive"], sent["neutral"], sent["negative"]],
        hole=0.55,
        marker_colors=["#22c55e", "#94a3b8", "#ef4444"],
        textinfo="label+percent",
        textfont=dict(color="#111827", size=13),
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Sentiment Breakdown", font=dict(color="#111827", size=16)),
        height=280,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        paper_bgcolor="white",
        font=dict(color="#111827"),
    )
    return fig


def _kpis_bar(kpis: dict) -> go.Figure:
    labels = ["Posts", "Comments", "Avg Upvotes", "Pain Score (×10)", "Feature Req.", "Subreddits"]
    values = [
        kpis["total_posts"],
        kpis["total_comments"],
        kpis["avg_upvotes"],
        kpis["avg_pain_score"] * 10,
        kpis["feature_request_count"],
        kpis["subreddits_found"],
    ]
    colors = ["#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444", "#10b981", "#06b6d4"]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        textfont=dict(color="#111827", size=12),
        hovertemplate="%{x}: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Data Collection Overview", font=dict(color="#111827", size=16)),
        height=320,
        margin=dict(l=10, r=10, t=50, b=50),
        yaxis_title="Count / Value",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#111827"),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#111827", size=12))
    fig.update_yaxes(gridcolor="#e5e7eb", tickfont=dict(color="#111827"))
    return fig


def _subreddits_bar(top_subs: list) -> go.Figure:
    if not top_subs:
        return None
    names = [f"r/{s['subreddit']}" for s in top_subs]
    counts = [s["post_count"] for s in top_subs]
    fig = go.Figure(go.Bar(
        x=counts, y=names, orientation="h",
        marker_color="#6366f1",
        text=counts,
        textposition="outside",
        textfont=dict(color="#111827", size=12),
        hovertemplate="%{y}: %{x} posts<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Top Subreddits", font=dict(color="#111827", size=16)),
        height=max(280, len(names) * 36 + 80),
        margin=dict(l=160, r=60, t=50, b=30),
        xaxis_title="Post Count",
        yaxis={"autorange": "reversed"},
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#111827", size=13),
    )
    fig.update_xaxes(
        gridcolor="#e5e7eb",
        tickfont=dict(color="#111827"),
        title_font=dict(color="#111827"),
    )
    fig.update_yaxes(
        showgrid=False,
        tickfont=dict(color="#111827", size=13),
    )
    return fig


def _pros_cons_bar(pros: list, cons: list) -> go.Figure:
    fig = go.Figure([
        go.Bar(name="Pros", x=["Evidence Points"], y=[len(pros)], marker_color="#22c55e",
               text=[len(pros)], textposition="outside", textfont=dict(color="#111827")),
        go.Bar(name="Cons / Contradictions", x=["Evidence Points"], y=[len(cons)], marker_color="#ef4444",
               text=[len(cons)], textposition="outside", textfont=dict(color="#111827")),
    ])
    fig.update_layout(
        title=dict(text="Pros vs Contradictions", font=dict(color="#111827", size=16)),
        barmode="group",
        height=260,
        margin=dict(l=10, r=10, t=50, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#111827"),
        legend=dict(font=dict(color="#111827")),
    )
    fig.update_xaxes(tickfont=dict(color="#111827"), showgrid=False)
    fig.update_yaxes(tickfont=dict(color="#111827"), gridcolor="#e5e7eb")
    return fig


def _swot_fig(swot: dict) -> go.Figure:
    quadrants = [
        ("💪 Strengths",     swot.get("strengths", []),     "#dcfce7", "#166534"),
        ("⚠️ Weaknesses",    swot.get("weaknesses", []),    "#fee2e2", "#991b1b"),
        ("🚀 Opportunities", swot.get("opportunities", []), "#dbeafe", "#1e40af"),
        ("🔥 Threats",       swot.get("threats", []),       "#fef9c3", "#92400e"),
    ]
    cells = []
    for title, items, _bg, _color in quadrants:
        text = f"<b>{title}</b><br><br>" + "<br>".join(
            f"• {item[:90]}{'…' if len(item) > 90 else ''}" for item in items
        )
        cells.append(text)

    fig = go.Figure(go.Table(
        header=dict(
            values=["<b>💪 Strengths</b>", "<b>⚠️ Weaknesses</b>",
                    "<b>🚀 Opportunities</b>", "<b>🔥 Threats</b>"],
            fill_color=["#dcfce7", "#fee2e2", "#dbeafe", "#fef9c3"],
            font=dict(size=13, color=["#166534", "#991b1b", "#1e40af", "#92400e"]),
            align="center",
            height=40,
        ),
        cells=dict(
            values=[[cells[0]], [cells[1]], [cells[2]], [cells[3]]],
            fill_color=["#f0fdf4", "#fff5f5", "#eff6ff", "#fffbeb"],
            font=dict(size=11),
            align="left",
            height=30,
        ),
    ))
    fig.update_layout(
        title="SWOT Analysis",
        margin=dict(l=5, r=5, t=40, b=5),
        height=max(350, max(
            len(swot.get("strengths", [])),
            len(swot.get("weaknesses", [])),
            len(swot.get("opportunities", [])),
            len(swot.get("threats", [])),
        ) * 35 + 120),
    )
    return fig


def _score_timeline(buzz: int, validation: int) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Buzz Score", x=["Buzz"], y=[buzz],
        marker_color="#3b82f6",
        text=[f"{buzz}/100"], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Validation Score", x=["Validation"], y=[validation],
        marker_color="#10b981",
        text=[f"{validation}/100"], textposition="outside",
    ))
    fig.update_layout(
        title="Score Overview",
        barmode="group",
        height=280,
        yaxis={"range": [0, 110]},
        margin=dict(l=10, r=10, t=40, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
    )
    return fig


# ── Screen 1: Idea Input ──────────────────────────────────────────────────────

def screen_input():
    key_ok = sidebar_provider_settings()
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.title("🔍 IdeaValidator")
        st.markdown("##### Validate your startup idea with real data — Reddit, web & AI agents")
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
            if not key_ok:
                st.error("Please configure an AI provider and API key in the sidebar first.")
                return
            with st.spinner("Analyzing your idea..."):
                result = api_post("/validate", {"idea": idea.strip(), "llm_config": _llm_config()})
            if result:
                st.session_state.run_id = result["run_id"]
                st.session_state.questions = result["questions"]
                st.session_state.screen = "questions"
                st.rerun()

    with col_right:
        st.markdown("")
        st.markdown("**What you'll get:**")
        st.markdown("""
🔥 **Buzz & Validation Scores** with gauges
📊 **Interactive charts** — sentiment, KPIs, subreddits
✅ **Pros** backed by real post data
🔴 **Contradictions** that challenge your core idea
🔷 **Full SWOT analysis**
🌐 **Web research** — Wikipedia + top articles
💬 **Real quotes** from the community
🧠 **AI reasoning** + market insights
        """)
        st.markdown("---")
        st.markdown("*4 AI agents run in parallel for speed.*")


# ── Screen 2: Clarifying Questions ────────────────────────────────────────────

def screen_questions():
    sidebar_provider_settings()
    st.title("🎯 A few quick questions")
    st.markdown("The AI needs context to run better, more targeted research. Takes 30 seconds.")
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
                result = api_post(f"/answers/{st.session_state.run_id}", {"answers": answers})
            if result:
                st.session_state.screen = "status"
                st.rerun()


# ── Screen 3: Pipeline Status ─────────────────────────────────────────────────

def screen_status():
    sidebar_provider_settings()
    run_id = st.session_state.run_id
    data = api_get(f"/status/{run_id}")
    if not data:
        return

    if data.get("_not_found"):
        st.warning("The server was restarted and lost your session. Please start over.")
        if st.button("Start Over"):
            for k, v in [("run_id", None), ("questions", []), ("screen", "input")]:
                st.session_state[k] = v
            st.rerun()
        return

    status = data.get("status", "unknown")
    st.title("🔬 Research in Progress")
    st.markdown(f"Run ID: `{run_id}`")
    st.markdown("---")

    current_idx = STAGE_KEYS.index(status) if status in STAGE_KEYS else -1
    for i, (_stage_key, label, icon) in enumerate(PIPELINE_STAGES):
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
    sidebar_provider_settings()
    run_id = st.session_state.run_id
    data = api_get(f"/report/{run_id}")
    if not data:
        st.error("Could not load the report.")
        return

    sent = data["sentiment"]
    kpis = data["kpis"]
    swot = data.get("swot", {})
    web = data.get("web_findings", {})

    st.title("📊 Validation Report")
    st.markdown(f"Run ID: `{run_id}`")

    # ── Top-level score row ───────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🔥 Buzz", f"{data['buzz_score']} / 100")
    c2.metric("✅ Validation", f"{data['validation_score']} / 100")
    c3.metric("😊 Positive", f"{sent['positive']}%")
    c4.metric("😟 Negative", f"{sent['negative']}%")
    c5.metric("📄 Posts", kpis["total_posts"])

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_overview, tab_pros_cons, tab_swot, tab_web, tab_quotes = st.tabs([
        "📈 Overview", "✅ Pros & Cons", "🔷 SWOT", "🌐 Web Research", "💬 Quotes & Reasoning"
    ])

    # ── Tab 1: Overview ───────────────────────────────────────────────────────
    with tab_overview:
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(_gauge(data["buzz_score"], "🔥 Buzz Score", "#3b82f6"),
                            use_container_width=True, theme=None)
        with g2:
            st.plotly_chart(_gauge(data["validation_score"], "✅ Validation Score", "#10b981"),
                            use_container_width=True, theme=None)

        ch1, ch2 = st.columns([1, 1])
        with ch1:
            st.plotly_chart(_sentiment_donut(sent), use_container_width=True, theme=None)
        with ch2:
            st.plotly_chart(_kpis_bar(kpis), use_container_width=True, theme=None)

        sub_fig = _subreddits_bar(kpis.get("top_subreddits", []))
        if sub_fig:
            st.plotly_chart(sub_fig, use_container_width=True, theme=None)

        # Extra KPI metrics row
        st.markdown("#### Raw Metrics")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Comments", kpis["total_comments"])
        k2.metric("Avg Upvotes", kpis["avg_upvotes"])
        k3.metric("Avg Pain Score", kpis["avg_pain_score"])
        k4.metric("Feature Requests", kpis["feature_request_count"])
        k5.metric("Pain Posts %", f"{kpis.get('pain_posts_ratio', 0)}%")

    # ── Tab 2: Pros & Cons ────────────────────────────────────────────────────
    with tab_pros_cons:
        st.plotly_chart(_pros_cons_bar(data["pros"], data["cons"]),
                        use_container_width=True, theme=None)
        st.markdown("---")

        col_pros, col_cons = st.columns(2)
        with col_pros:
            st.subheader("✅ Pros — Demand Signals")
            for item in data["pros"]:
                st.success(f"• {item}")

        with col_cons:
            st.subheader("🔴 Contradictions to Core Idea")
            st.caption("These challenge the fundamental premise, not just operational risks.")
            for item in data["cons"]:
                st.error(f"• {item}")

    # ── Tab 3: SWOT ───────────────────────────────────────────────────────────
    with tab_swot:
        if swot:
            st.plotly_chart(_swot_fig(swot), use_container_width=True, theme=None)
            st.markdown("---")
            sw1, sw2 = st.columns(2)
            with sw1:
                with st.expander("💪 Strengths", expanded=True):
                    for s in swot.get("strengths", []):
                        st.markdown(f"- {s}")
                with st.expander("🚀 Opportunities", expanded=True):
                    for o in swot.get("opportunities", []):
                        st.markdown(f"- {o}")
            with sw2:
                with st.expander("⚠️ Weaknesses", expanded=True):
                    for w in swot.get("weaknesses", []):
                        st.markdown(f"- {w}")
                with st.expander("🔥 Threats", expanded=True):
                    for t in swot.get("threats", []):
                        st.markdown(f"- {t}")
        else:
            st.info("SWOT data not available.")

    # ── Tab 4: Web Research ───────────────────────────────────────────────────
    with tab_web:
        insights = data.get("market_insights", [])
        if insights:
            st.subheader("🧩 Market Insights")
            for ins in insights:
                st.info(f"💡 {ins}")
            st.markdown("---")

        wiki = web.get("wikipedia_summary", "")
        if wiki:
            st.subheader("📖 Wikipedia Context")
            st.markdown(wiki)
            st.markdown("---")

        results = web.get("top_results", [])
        if results:
            st.subheader(f"🌐 Web Search Results ({len(results)} sources)")
            for r in results:
                with st.expander(r.get("title", "Source")):
                    st.markdown(f"**URL:** {r.get('url', '')}")
                    st.markdown(r.get("snippet", ""))
        else:
            st.info("No web results available.")

    # ── Tab 5: Quotes & Reasoning ─────────────────────────────────────────────
    with tab_quotes:
        st.subheader("💬 Real Quotes from the Community")
        quotes = data.get("key_quotes", [])
        if quotes:
            for i, q in enumerate(quotes):
                st.markdown(f"> *\"{q}\"*")
                if i < len(quotes) - 1:
                    st.markdown("")
        else:
            st.info("No quotes available.")

        st.markdown("---")
        st.subheader("🧠 AI Analysis & Reasoning")
        st.info(data.get("reasoning", "No reasoning available."))

    st.markdown("---")
    if st.button("🔄 Validate Another Idea"):
        for k, v in [("run_id", None), ("questions", []), ("screen", "input")]:
            st.session_state[k] = v
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
