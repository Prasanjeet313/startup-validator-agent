# IdeaValidator — Startup Idea Validation Agent

Validate your startup idea using real Reddit data and AI analysis. Now supports multiple LLM providers: **Groq, Google Gemini, OpenAI, Anthropic, and Ollama (local)**.

---

## Prerequisites

- Python 3.10 or higher
- pip

---

## 1. Clone / Navigate to the Project

```bash
cd startup-validator-agent
```

---

## 2. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure API Keys

The `.env` file is already created with your Groq and Gemini keys. You can open it to add or change keys:

```
.env
```

```dotenv
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here

# Optional — add if you have these
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
YOUTUBE_API_KEY=
```

> Keys set in `.env` are used automatically. You can also paste a key directly in the UI sidebar without touching `.env`.

---

## 5. Run the Backend (FastAPI)

Open a terminal, activate the virtual environment, then run:

```bash
uvicorn backend.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Leave this terminal open.

---

## 6. Run the Frontend (Streamlit)

Open a **second** terminal, activate the virtual environment, then run:

```bash
streamlit run frontend/app.py
```

Streamlit will open automatically at `http://localhost:8501`.

---

## 7. Using the App

### Sidebar — AI Provider Settings

On the left sidebar you will see **⚙️ AI Provider**:

1. **Provider** — choose from: Groq, Google Gemini, OpenAI, Anthropic, Ollama (Local)
2. **Model** — select a model from the provider's available list
3. **API Key** — if your key is already in `.env` it says *"Using key from .env"*. You can also paste a key here to override.
4. A green **✅ ready** badge confirms the provider is configured.

### Main Flow

1. **Describe your idea** → click *Validate My Idea*
2. **Answer 4–5 clarifying questions** to help the AI focus the research
3. **Watch the pipeline** run in real time (query generation → Reddit scraping → AI analysis)
4. **Read your report** — Buzz Score, Validation Score, Pros/Cons, real quotes, and AI reasoning

---

## Available Providers & Models

| Provider | Models | Key source |
|---|---|---|
| **Groq** | llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768, gemma2-9b-it | `GROQ_API_KEY` in `.env` |
| **Google Gemini** | gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash | `GEMINI_API_KEY` in `.env` |
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-3.5-turbo | `OPENAI_API_KEY` in `.env` |
| **Anthropic** | claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5-20251001 | `ANTHROPIC_API_KEY` in `.env` |
| **Ollama (Local)** | llama3, llama3.1, mistral, codellama, phi3 | No key needed — must be running locally |

### Getting API Keys

- **Groq** (free tier): https://console.groq.com/keys
- **Google Gemini** (free tier): https://aistudio.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/account/keys
- **Ollama** (local, free): https://ollama.com — run `ollama serve` before starting the app

---

## Project Structure

```
startup-validator-agent/
├── .env                          # Your API keys (gitignored)
├── requirements.txt
├── backend/
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Shared config (Reddit headers, data dir)
│   ├── llm_provider.py           # Provider abstraction (Groq/Gemini/OpenAI/Anthropic/Ollama)
│   ├── state.py                  # In-memory run state
│   ├── agents/
│   │   ├── clarification_agent.py
│   │   ├── query_agent.py
│   │   └── analysis_agent.py
│   ├── models/
│   │   ├── idea.py               # IdeaInput, LLMConfig, IdeaBrief, QueryPlan
│   │   └── report.py             # ValidationReport, KPIs, SentimentBreakdown
│   ├── routers/
│   │   └── validate.py           # API endpoints including GET /providers
│   ├── scrapers/
│   │   └── reddit_scraper.py
│   └── storage/
│       └── excel_writer.py
├── frontend/
│   └── app.py                    # Streamlit UI with provider sidebar
└── data/
    └── runs/                     # Excel files saved per run
```

---

## Troubleshooting

**"Cannot connect to the API"** — make sure `uvicorn` is running on port 8000 (Step 5).

**"No API key for groq"** — check that `GROQ_API_KEY` is set in `.env` and the backend was started after the `.env` file was created.

**Anthropic errors** — make sure `anthropic` is installed: `pip install anthropic`.

**Ollama not working** — start the Ollama server first: `ollama serve`, then pull a model: `ollama pull llama3`.
