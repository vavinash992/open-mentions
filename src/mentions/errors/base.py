from typing import Any, Optional


class CustomException(Exception):
    """
    Base class for custom exceptions
    """

    def __init__(
        self,
        message: Optional[str] = None,
        extra_info: Optional[dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        self.message = message
        self.extra_info = extra_info
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.extra_info:
            return f"{self.message or ''} (Extra Info: {self.extra_info})"
        return self.message or ""
