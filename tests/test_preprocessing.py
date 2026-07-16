import pytest
import pandas as pd
from src.data.ingestion import (
    _normalize_cost,
    _normalize_rating,
    _normalize_location,
    _normalize_cuisines,
)


def test_normalize_cost():
    assert _normalize_cost("₹300 for two") == 300
    assert _normalize_cost("1,200") == 1200
    assert _normalize_cost("N/A") is None
    assert _normalize_cost(None) is None
    assert _normalize_cost(500) == 500


def test_normalize_rating():
    assert _normalize_rating("4.2") == 4.2
    assert _normalize_rating("4.2/5") == 4.2
    assert _normalize_rating("NEW") is None
    assert _normalize_rating("-") is None
    assert _normalize_rating("") is None
    assert _normalize_rating("   ") is None
    assert _normalize_rating(None) is None


def test_normalize_location():
    assert _normalize_location(" New Delhi ") == "new delhi"
    assert _normalize_location("MUMBAI") == "mumbai"
    assert _normalize_location(None) is None


def test_normalize_cuisines():
    assert _normalize_cuisines("North Indian, Chinese") == ["north indian", "chinese"]
    assert _normalize_cuisines("Italian") == ["italian"]
    assert _normalize_cuisines("   Fast Food  ,  Beverages ") == [
        "fast food",
        "beverages",
    ]
    assert _normalize_cuisines("") is None
    assert _normalize_cuisines("   ") is None
    assert _normalize_cuisines(None) is None


from unittest.mock import patch, Mock


import sys


@pytest.fixture
def mock_datasets_module():
    mock_module = Mock()
    with patch.dict("sys.modules", {"datasets": mock_module}):
        yield mock_module


@patch("pandas.read_parquet")
def test_dataframe_preprocessing(mock_read_parquet, mock_datasets_module):
    # Mock load_and_preprocess to avoid actual download and test DataFrame operations
    import src.data.ingestion as ingestion

    mock_raw_data = pd.DataFrame(
        {
            "name": ["A", "B", "C", "A", "D"],
            "rate": ["4.5", "NEW", "-", "4.5", "3.0/5"],
            "approx_cost(for two people)": [
                "₹500 for two",
                "1,000",
                "N/A",
                "₹500 for two",
                "300",
            ],
            "cuisines": [
                "Italian, Chinese",
                "Indian",
                "Fast Food",
                "Italian, Chinese",
                None,
            ],
            "location": [" Delhi ", "mumbai", "Pune", " Delhi ", "Goa"],
        }
    )

    mock_datasets_module.load_dataset.return_value = Mock(
        to_pandas=lambda: mock_raw_data.copy()
    )
    mock_read_parquet.side_effect = FileNotFoundError

    df = ingestion.load_and_preprocess(cache_path=None)

    # Assert columns
    assert list(df.columns) == ["name", "location", "cuisines", "cost", "rating"]

    # C should be dropped because cost is N/A
    # D should be dropped because cuisines is None
    # Duplicate A should be dropped
    # Expected remaining: A, B

    assert len(df) == 2

    # Assert A
    row_a = df[df["name"] == "A"].iloc[0]
    assert row_a["cost"] == 500
    assert row_a["rating"] == 4.5
    assert row_a["location"] == "delhi"
    assert row_a["cuisines"] == ["italian", "chinese"]

    # Assert B
    row_b = df[df["name"] == "B"].iloc[0]
    assert row_b["cost"] == 1000
    assert pd.isna(row_b["rating"])  # "NEW" -> None / np.nan
