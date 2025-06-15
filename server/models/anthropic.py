import os

from anthropic import Anthropic

from ..errors import InvalidAPIKey, MissingEnvironmentVariables, UnsupportedModel
from .base import BaseModel
from .types import CompletionResponse

class AnthropicModel(BaseModel):
    DEFAULT_MODEL_NAME = "claude-3-5-sonnet"

    def __init__(self):
        """
        Initialize the AnthropicModel instance.
        This constructor sets up the Anthropic client by calling the initialize_client method.
        """
        self.initialize_client()
        self.supported_models = [
            "claude-3-5-sonnet",
            "claude-3-5-haiku",
            "claude-3-5-sonnet",
            "claude-3-haiku",
            "claude-3-opus",
            "claude-3-sonnet",
        ]
        if os.getenv("MODEL_NAME") is not None:
            self.validate_model(os.getenv("MODEL_NAME"))

    def validate_model(self, model_name):
        """
        Validate the model name against the supported models.
        """
        all_models = [model.id for model in self.client.models.list()]
        for supported_model in self.supported_models:
            if model_name.startswith(supported_model):
                if supported_model not in all_models:
                    raise UnsupportedModel(f"The model '{model_name}' is not supported by the API. Please recheck your model name.")
                return
        raise UnsupportedModel(f"The model '{model_name}' is not currently supported. Supported models are: {', '.join(self.supported_models)}.")

    def initialize_client(self):
        """
        Initialize the Anthropic client.
        This method sets up the Anthropic client with the API key.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise MissingEnvironmentVariables("ANTHROPIC_API_KEY is not set in the environment variables.")
        self.client = Anthropic(api_key=api_key)
        try:
            self.client.models.list()
        except Exception as e:
            raise InvalidAPIKey(f"The provided Anthropic API key is invalid or has insufficient permissions: {str(e)}")

    def make_llm_request(self, messages):
        """
        Make a request to the LLM using the Anthropic client.
        
        :param messages: The messages to send to the LLM.
        :return: The response from the LLM.
        """
        model_name = os.getenv("MODEL_NAME", self.DEFAULT_MODEL_NAME)
        response = self.client.messages.create(
            model=model_name,
            messages=messages,
            max_tokens=6000,
            temperature=0.05,
        )
        return CompletionResponse(
            content=response.content,
            input_token=response.usage.input_tokens,
            output_token=response.usage.output_tokens,
            cached_token=response.usage.cache_read_input_tokens
        )

