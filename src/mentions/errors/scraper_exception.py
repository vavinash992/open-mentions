from .base import CustomException


class InValidFilterException(CustomException):
    """
    Exception raised when an invalid filter is provided to the scraper.
    """

    def __init__(self, filter_by: str, valid_filters: list[str]):
        message = f"Invalid filter '{filter_by}'. Valid filters are: {', '.join(valid_filters)}."
        super().__init__(message=message, extra_info={"filter": filter_by, "valid_filters": valid_filters})
