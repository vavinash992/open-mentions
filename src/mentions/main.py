from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Open Mentions API",
    description="API for managing and retrieving mentions in the Open Mentions project.",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
