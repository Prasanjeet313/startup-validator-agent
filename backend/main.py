import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import validate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="IdeaValidator API",
    version="0.1.0",
    description="Multi-agent idea validation pipeline — Reddit research + AI analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(validate.router, tags=["validation"])


@app.get("/ping")
def ping():
    """Health check."""
    return {"status": "ok"}
