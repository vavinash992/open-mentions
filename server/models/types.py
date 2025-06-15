from dataclasses import dataclass

@dataclass
class CompletionResponse:
    """
    Class representing request of a completion.
    """
    content : str
    input_token: int
    output_token: int
    cached_token: int