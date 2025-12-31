"""
Retry utilities using tenacity
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openai import RateLimitError, APIError
from src.utils.config import settings


def retry_openai(func):
    """Retry decorator for OpenAI API calls"""
    return retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        reraise=True,
    )(func)

