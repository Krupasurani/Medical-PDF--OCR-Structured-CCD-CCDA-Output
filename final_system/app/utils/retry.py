"""Retry utilities with exponential backoff"""

import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

from .logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_delay: float = 32.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """Decorator for exponential backoff retry logic

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for exponential backoff
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function with retry logic
    """
    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            "Max retries exceeded",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e),
                        )
                        raise

                    logger.warning(
                        "Retry attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e),
                    )

                    time.sleep(delay)
                    delay = min(delay * backoff_multiplier, max_delay)

            # Should never reach here, but for type safety
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop termination")

        return wrapper

    return decorator
