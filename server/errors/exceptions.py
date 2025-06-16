from typing import Optional

from server.errors.base import CustomException


class MissingEnvironmentVariables(CustomException):
    """Exception raised when environment variables are missing."""

    def __init__(
        self,
        message: str,
        extra_info: Optional[dict] = None,
    ):
        super().__init__(message, extra_info)

class InvalidAPIKey(CustomException):
    """Exception raised when the API key is invalid."""

    def __init__(
        self,
        message: str,
        extra_info: Optional[dict] = None,
    ):
        super().__init__(message, extra_info)

class UnsupportedModel(CustomException):
    """Exception raised when the model is not supported."""

    def __init__(
        self,
        message: str,
        extra_info: Optional[dict] = None,
    ):
        super().__init__(message, extra_info)

class MissingDeploymentName(CustomException):
    """Exception raised when the deployment name is missing."""

    def __init__(
        self,
        message: str,
        extra_info: Optional[dict] = None,
    ):
        super().__init__(message, extra_info)