class GroqClientError(Exception):
    """Base exception for Groq client errors."""

    pass


class ConfigError(GroqClientError):
    """Raised when configuration (e.g. API key) is missing or invalid."""

    pass


class ApiTimeoutError(GroqClientError):
    """Raised when the Groq API call times out after retries."""

    pass


class ApiRateLimitError(GroqClientError):
    """Raised when the Groq API rate limit is exceeded and retries are exhausted."""

    pass


class ModelUnavailableError(GroqClientError):
    """Raised when the requested model is unavailable."""

    pass
