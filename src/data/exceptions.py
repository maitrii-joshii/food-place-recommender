class DataIngestionError(Exception):
    """Base class for data ingestion exceptions."""

    pass


class SchemaError(DataIngestionError):
    """Raised when the loaded dataset is missing required columns."""

    pass


class DatasetLoadError(DataIngestionError):
    """Raised when the dataset fails to load from the source."""

    pass


class EmptyDatasetError(DataIngestionError):
    """Raised when the dataset has zero rows after loading or preprocessing."""

    pass
