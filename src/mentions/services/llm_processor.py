"""LLM Processor Service for classifying scraped items."""

import os
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from mentions.scrapers.base import ScrapedItem


class ClassificationResult(BaseModel):
    """Structured output from LLM classification."""

    is_relevant: bool = Field(..., description="Is this mention actually about the target company?")
    sentiment: str = Field(..., description="Sentiment: 'positive', 'negative', or 'neutral'")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(..., description="Short explanation of the classification")
    emotion: str | None = Field(
        None,
        description="Primary emotion: 'frustration', 'joy', 'curiosity', 'disappointment', 'anger', 'neutral', 'excitement', 'concern', 'satisfaction', 'confusion'",
    )
    summary: str | None = Field(None, max_length=150, description="Concise one-sentence summary (max 150 characters)")


class LLMProcessor:
    """Async service for classifying ScrapedItem using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM Processor.

        Args:
            api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY env var.
            model: OpenAI model to use for classification. Defaults to gpt-4o-mini.
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            msg = "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            raise ValueError(msg)

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def classify(
        self, item: ScrapedItem, company_name: str, include_detailed: bool = True
    ) -> ClassificationResult:
        """
        Classify a ScrapedItem using LLM.

        Args:
            item: The ScrapedItem to classify.
            company_name: The target company name to check relevance against.
            include_detailed: If True, includes emotion and summary. If False, only does basic classification.

        Returns:
            ClassificationResult with is_relevant, sentiment, confidence_score, reasoning, emotion, and summary.
        """
        prompt = self._build_prompt(item, company_name, include_detailed)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing social media mentions and determining their relevance, sentiment, emotions, and summarizing content for companies. Always respond with valid JSON matching the required schema. Be objective and ignore gibberish or common social media filler when summarizing.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent classification
            )

            result_text = response.choices[0].message.content
            if not result_text:
                msg = "Empty response from OpenAI API"
                raise ValueError(msg)  # noqa: TRY301

            # Parse the JSON response
            import json

            result_dict = json.loads(result_text)

            # Validate and return structured result
            return ClassificationResult(**result_dict)

        except Exception as e:
            # Fallback to neutral classification on error
            fallback_emotion = "neutral" if include_detailed else None
            fallback_summary = "Unable to generate summary due to classification error." if include_detailed else None
            return ClassificationResult(
                is_relevant=False,
                sentiment="neutral",
                confidence_score=0.0,
                reasoning=f"Classification error: {e!s}",
                emotion=fallback_emotion,
                summary=fallback_summary,
            )

    def _build_prompt(self, item: ScrapedItem, company_name: str, include_detailed: bool = True) -> str:
        """Build the classification prompt for the LLM."""
        emotion_instructions = (
            """
    "emotion": "frustration" | "joy" | "curiosity" | "disappointment" | "anger" | "neutral" | "excitement" | "concern" | "satisfaction" | "confusion",  // Primary emotion detected in the text
    "summary": "One concise sentence (max 150 chars)"  // Objective summary ignoring gibberish/filler
"""
            if include_detailed
            else ""
        )

        emotion_guidance = (
            """
- emotion: Classify the PRIMARY emotion expressed. Choose from: frustration, joy, curiosity, disappointment, anger, neutral, excitement, concern, satisfaction, confusion. Be specific but choose the dominant emotion.
- summary: Write a concise, objective one-sentence summary (max 150 characters). Focus on what the mention actually discusses. Ignore gibberish, common social media filler (like "lol", "tbh", excessive emojis), and repetitive phrases. Extract the core message or concern.
"""
            if include_detailed
            else ""
        )

        return f"""Analyze the following social media mention and classify it:

Company to check relevance against: {company_name}

Platform: {item.platform}
Content: {item.content}
URL: {item.url}
Keyword searched: {item.keyword}

Please provide a JSON response with the following structure:
{{
    "is_relevant": true/false,  // Is this mention actually about the target company "{company_name}"?
    "sentiment": "positive" | "negative" | "neutral",  // What is the sentiment toward the company?
    "confidence_score": 0.0-1.0,  // How confident are you in this classification?
    "reasoning": "Brief explanation of your classification"  // 1-2 sentences explaining your decision{emotion_instructions}
}}

Important considerations:
- is_relevant should be true ONLY if the mention is clearly about "{company_name}" or their products/services
- sentiment should reflect the overall tone: positive (favorable/praising), negative (critical/complaining), or neutral (factual/mixed)
- confidence_score should be higher when the mention is clear and unambiguous
- reasoning should be concise and explain your decision{emotion_guidance}

JSON Response:"""
