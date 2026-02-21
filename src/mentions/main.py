from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from mentions.api.v1.analytics import analytics_router
from mentions.db.session import init_db
from mentions.routers import export, history, keywords, monitor, search, workspace
from mentions.services.monitoring_scheduler import get_scheduler

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI startup and shutdown."""
    # Startup: Initialize database and start scheduler
    await init_db()

    # Start the monitoring scheduler
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("FastAPI application started with scheduled monitoring enabled")

    yield

    # Shutdown: Stop scheduler
    scheduler.stop()
    logger.info("FastAPI application shutting down - scheduler stopped")


app = FastAPI(
    title="Open Mentions API",
    description="API for managing and retrieving mentions in the Open Mentions project.",
    version="0.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(search.search_router)
app.include_router(history.history_router)
app.include_router(monitor.monitor_router)
app.include_router(keywords.keywords_router)
app.include_router(workspace.workspace_router)
app.include_router(analytics_router)
app.include_router(export.export_router)


@app.get("/")
async def root(request: Request):
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Open Mentions API is running!"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API status.
    """
    return {"status": "healthy"}
