from fastapi import APIRouter

reddit_router = APIRouter(prefix="/reddit", tags=["reddit"])


@reddit_router.post("/mentions")
async def create_reddit_mention(mention: str):
    """
    Create a new mention in Reddit.
    """
    return {"message": "Reddit mention created!", "mention": mention}
