from abc import ABC, abstractmethod

class BaseModel(ABC):
    """
    Abstract base class for all models.
    Defines the interface that all models must implement.
    """
    __slots__ = ["client"]

    @abstractmethod
    def initialize_client(self):
        """
        Initialize the client connection.
        This method should be implemented by subclasses to set up the client.
        """
        pass
    
    @abstractmethod
    def make_llm_request(self, request):
        """
        Make a request to the LLM.
        This method should be implemented by subclasses to handle LLM requests.
        
        :param request: The request object containing the necessary parameters.
        :return: The response from the LLM.
        """
        pass