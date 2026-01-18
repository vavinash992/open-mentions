"""LLM Processor Service for classifying and summarizing scraped items using Azure OpenAI and instructor."""

import os
from typing import Optional

import instructor
from loguru import logger
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field

from mentions.scrapers.base import ScrapedItem


class ClassificationResult(BaseModel):
    """Structured output from LLM classification and summarization."""

    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score indicating how relevant the mention is to the target company (0.0 to 1.0).",
    )
    is_relevant: bool = Field(..., description="Is this mention actually about the target company?")
    sentiment: str = Field(
        ...,
        description="Sentiment: 'positive', 'negative', or 'neutral'",
    )
    emotion: str = Field(
        ...,
        description="Primary emotion: 'frustration', 'joy', 'curiosity', 'disappointment', 'anger', 'neutral', 'excitement', 'concern', 'satisfaction', 'confusion'",
    )
    summary: str = Field(..., max_length=150, description="Concise one-sentence summary (max 150 characters)")


class LLMProcessor:
    """Async service for classifying and summarizing ScrapedItem using Azure OpenAI API with instructor for structured outputs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        """
        Initialize the LLM Processor with Azure OpenAI.

        Args:
            api_key: Azure OpenAI API key. If None, will try to get from AZURE_OPENAI_API_KEY env var.
            endpoint: Azure OpenAI endpoint. If None, will try to get from AZURE_OPENAI_ENDPOINT env var.
            deployment_name: Azure OpenAI deployment name. If None, will try to get from AZURE_OPENAI_DEPLOYMENT_NAME env var.
            api_version: Azure OpenAI API version. If None, will try to get from AZURE_OPENAI_API_VERSION env var.
        """
        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
        api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

        if not api_key:
            msg = "Azure OpenAI API key is required. Set AZURE_OPENAI_API_KEY environment variable."
            raise ValueError(msg)
        if not endpoint:
            msg = "Azure OpenAI endpoint is required. Set AZURE_OPENAI_ENDPOINT environment variable."
            raise ValueError(msg)

        # Initialize Azure OpenAI client
        azure_client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint.rstrip("/"),  # Remove trailing slash if present
        )

        # Wrap client with instructor for structured outputs
        # Use patch() to enable structured outputs on the Azure client
        self.instructor_client = instructor.patch(azure_client)

        self.deployment_name = deployment_name
        self.api_version = api_version

        logger.info(f"LLMProcessor initialized with deployment: {deployment_name} at {endpoint}")

    async def classify_and_summarize(self, item: ScrapedItem, company_name: str) -> ClassificationResult:
        """
        Classify and summarize a single ScrapedItem using Azure OpenAI with structured output.

        This method extracts:
        - relevance_score: How relevant the mention is to the company (0.0-1.0)
        - is_relevant: Boolean indicating if mention is about the company
        - sentiment: Positive, negative, or neutral sentiment
        - emotion: Primary emotion detected
        - summary: One-sentence summary of the mention

        Args:
            item: The ScrapedItem to classify and summarize.
            company_name: The target company name to check relevance against.

        Returns:
            ClassificationResult with all extracted fields populated.

        Raises:
            Exception: If classification fails, returns a default ClassificationResult.
        """
        prompt = self._build_classification_prompt(item, company_name)

        try:
            logger.debug(f"Classifying mention from {item.platform} for {company_name}")
            # Use instructor to get structured output from Azure OpenAI
            result = await self.instructor_client.chat.completions.create(
                model=self.deployment_name,
                response_model=ClassificationResult,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
            )

            logger.debug(
                f"Classification complete: relevance={result.relevance_score}, "
                f"sentiment={result.sentiment}, emotion={result.emotion}"
            )
        except Exception as e:
            logger.error(f"Error classifying mention {item.url}: {e}")
            # Fallback to neutral classification on error
            result = ClassificationResult(
                relevance_score=0.0,
                is_relevant=False,
                sentiment="neutral",
                emotion="neutral",
                summary=f"Classification error: {str(e)[:150]}",
            )
        return result

    async def classify(self, item: ScrapedItem, company_name: str) -> ClassificationResult:
        """
        Alias for classify_and_summarize for backward compatibility.

        Args:
            item: The ScrapedItem to classify.
            company_name: The target company name to check relevance against.

        Returns:
            ClassificationResult with all extracted fields.
        """
        return await self.classify_and_summarize(item, company_name)

    async def process_mentions(self, items: list[ScrapedItem], company_name: str) -> list[ScrapedItem]:
        """
        Process a list of mentions and populate classification fields using LLM.

        This method takes raw scraped items and enriches them with:
        - relevance_score
        - is_relevant
        - sentiment
        - emotion
        - summary

        Args:
            items: List of ScrapedItem objects to classify and summarize.
            company_name: The target company name to check relevance against.

        Returns:
            List of ScrapedItem objects with all classification fields populated.
        """
        import asyncio

        if not items:
            logger.info("No items to process")
            return items

        logger.info(f"Processing {len(items)} mentions for {company_name}")

        # Process all items concurrently
        tasks = [self.classify_and_summarize(item, company_name) for item in items]
        classifications = await asyncio.gather(*tasks, return_exceptions=True)

        # Update items with classification results
        processed_count = 0
        error_count = 0

        for item, classification in zip(items, classifications):
            if isinstance(classification, Exception):
                error_count += 1
                logger.error(f"Error classifying item {item.url}: {classification}")
                # Handle error case - set defaults
                item.relevance_score = 0.0
                item.is_relevant = False
                item.sentiment = "neutral"
                item.emotion = "neutral"
                item.summary = f"Classification error: {str(classification)[:150]}"
            elif isinstance(classification, ClassificationResult):
                processed_count += 1
                # Update item with classification results
                item.relevance_score = classification.relevance_score
                item.is_relevant = classification.is_relevant
                item.sentiment = classification.sentiment
                item.emotion = classification.emotion
                item.summary = classification.summary

        logger.info(f"Processed {processed_count} mentions successfully, {error_count} errors for {company_name}")

        return items

    def _get_system_prompt(self) -> str:
        """Get the system prompt for brand analysis."""
        return """You are an expert Brand Analyst specializing in social media mention analysis. Your role is to:

1. Determine if mentions are relevant to specific companies/brands
2. Classify sentiment (positive, negative, neutral)
3. Identify primary emotions expressed
4. Generate concise, objective summaries

Guidelines:
- Be precise in relevance scoring (0.0 = not relevant, 1.0 = highly relevant)
- Only mark as relevant if the mention clearly discusses the company, its products, services, or brand
- Sentiment should reflect overall tone toward the company
- Emotion should capture the primary feeling (frustration, joy, curiosity, disappointment, anger, neutral, excitement, concern, satisfaction, confusion)
- Summaries must be objective, concise (max 150 chars), and ignore social media filler/gibberish
- Focus on extracting core messages and concerns
- Summary should be exactly one sentence"""

    def _build_classification_prompt(self, item: ScrapedItem, company_name: str) -> str:
        """Build the classification and summarization prompt for the LLM."""
        return f"""Analyze the following social media mention for relevance to "{company_name}":

Platform: {item.platform}
Content: {item.content}
URL: {item.url}
Keyword searched: {item.keyword}

Extract the following information:
1. relevance_score: How relevant is this mention to "{company_name}"? (0.0 = not relevant, 1.0 = highly relevant)
2. is_relevant: Boolean - is this mention actually about "{company_name}" or their products/services?
3. sentiment: Overall sentiment toward the company (positive, negative, neutral)
4. emotion: Primary emotion expressed in the text (choose from: frustration, joy, curiosity, disappointment, anger, neutral, excitement, concern, satisfaction, confusion)
5. summary: A concise, objective ONE-SENTENCE summary (max 150 characters) of what the mention discusses. Ignore gibberish, filler words, and repetitive phrases. Extract the core message."""
