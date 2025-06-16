import os

from openai import AzureOpenAI
from openai._exceptions import AuthenticationError

from ..errors import InvalidAPIKey, MissingEnvironmentVariables, UnsupportedModel, MissingDeploymentName
from .base import BaseModel
from .types import CompletionResponse

class AzureOpenAIModel(BaseModel):
    DEFAULT_MODEL_NAME = "gpt-4-1"
    
    def __init__(self):
        """
        Initialize the AzureOpenAIModel instance.
        This constructor sets up the Azure OpenAI client by calling the initialize_client method.
        """
        self.initialize_client()
        self.supported_models = [
            "gpt-4",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.5",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
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
                    raise UnsupportedModel(f"The model '{model_name}' is not supported by the OpenAI API. Please recheck your model name.")
                return
        raise UnsupportedModel(f"The model '{model_name}' is not currently supported. Supported models are: {', '.join(self.supported_models)}.")
        

    def initialize_client(self):
        """
        Initialize the Azure OpenAI client.
        This method sets up the Azure OpenAI client with the API key.
        """
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_api_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not api_key:
            raise MissingEnvironmentVariables("AZURE_OPENAI_API_KEY is not set in the environment variables.")
        if not azure_api_deployment:
            raise MissingDeploymentName("AZURE_OPENAI_DEPLOYMENT_NAME is not set in the environment variables.")
        self.client = AzureOpenAI(
            azure_deployment=azure_api_deployment,
            api_version="2024-10-21",
            api_key=api_key
        )
        try:
            self.client.models.list()
        except AuthenticationError:
            raise InvalidAPIKey("The provided Azure OpenAI API key or deployment name is invalid or has insufficient permissions.")

    def make_llm_request(self, messages):
        """
        Make a request to the Azure OpenAI LLM.

        :param request: The request object containing the necessary parameters.
        :return: The response from the Azure OpenAI LLM.
        """
        model_name = os.environ.get("MODEL_NAME", self.DEFAULT_MODEL_NAME)

        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.05,
            seed=123,
        )
        return CompletionResponse(
            content=response.choices[0].message.content,
            input_token=response.usage.prompt_tokens,
            output_token=response.usage.completion_tokens,
            cached_token=response.usage.prompt_tokens_details.cached_tokens
        )
