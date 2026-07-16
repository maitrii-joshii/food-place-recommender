class FormatterError(Exception):
    """Base class for formatter errors."""

    pass


class EmptyResponseError(FormatterError):
    """Raised when the LLM returns an empty response."""

    pass


class JsonParsingError(FormatterError):
    """Raised when the LLM response cannot be parsed as JSON."""

    pass


class SchemaValidationError(FormatterError):
    """Raised when the parsed JSON does not match the expected schema."""

    pass
