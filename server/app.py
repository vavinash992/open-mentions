"""
FastAPI application template for open-mentions project.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager

from server.schemas import HealthResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Define the things to do when the application starts
    logger.info("Starting Open Mentions API")
    yield
    # Define the things to do when the application stops
    logger.info("Stopping Open Mentions API")


app = FastAPI(
    title="Open Mentions API",
    description="API for managing mentions and related functionality",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with basic API information
    """
    return {
        "message": "Welcome to Open Mentions API",
        "docs": "/docs",
        "health": "/health"
    }
    
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running
    """
    logger.info("Health check requested")
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )