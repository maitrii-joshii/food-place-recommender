import json
import pytest
from unittest.mock import patch, Mock
import sys
import pandas as pd


@pytest.fixture
def mock_datasets_module():
    mock_module = Mock()
    with patch.dict("sys.modules", {"datasets": mock_module}):
        yield mock_module


# ---------------------------------------------------------------------------
# End-to-End Integration Tests
# These tests use mocked HuggingFace + Groq to run the entire pipeline
# without any network calls.
# ---------------------------------------------------------------------------

# Minimal but realistic dataset fixture
MOCK_DATASET = pd.DataFrame(
    {
        "name": [
            "Spice Garden",
            "The Italian Job",
            "Delhi Darbar",
            "Dragon Palace",
            "Curry House",
        ],
        "rate": ["4.5", "4.2", "NEW", "3.8", "4.0"],
        "approx_cost(for two people)": ["₹600 for two", "₹800", "₹300", "₹500", "₹400"],
        "cuisines": [
            "North Indian, Mughlai",
            "Italian, Continental",
            "North Indian",
            "Chinese, Asian",
            "South Indian",
        ],
        "location": ["delhi", "delhi", "delhi", "delhi", "delhi"],
    }
)

MOCK_LLM_RESPONSE = json.dumps(
    {
        "recommendations": [
            {
                "rank": 1,
                "name": "Spice Garden",
                "explanation": "Top-rated North Indian restaurant within your budget.",
            },
            {
                "rank": 2,
                "name": "The Italian Job",
                "explanation": "Great Italian food with excellent reviews.",
            },
            {
                "rank": 3,
                "name": "Curry House",
                "explanation": "A solid South Indian option with good value.",
            },
        ]
    }
)


@patch("pandas.read_parquet")
@patch("src.groq_client.client.groq.Groq")
def test_happy_path_pipeline(mock_groq_class, mock_read_parquet, mock_datasets_module):
    """Full pipeline from preferences to parsed recommendations."""
    from src.data.ingestion import load_and_preprocess
    from src.filters.preferences import validate_preferences
    from src.filters.engine import filter_restaurants
    from src.prompt.builder import build_system_prompt, build_user_prompt
    from src.groq_client.client import GroqClient
    from src.formatter.parser import parse_llm_response

    # Mock dataset loading
    mock_datasets_module.load_dataset.return_value = Mock(
        to_pandas=lambda: MOCK_DATASET.copy()
    )
    mock_read_parquet.side_effect = FileNotFoundError

    # Mock Groq client
    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(content=MOCK_LLM_RESPONSE))]
    mock_groq_instance = Mock()
    mock_groq_instance.chat.completions.create.return_value = mock_completion
    mock_groq_class.return_value = mock_groq_instance

    # 1. Load data
    df = load_and_preprocess(cache_path=None)
    assert not df.empty

    # 2. Validate preferences
    prefs = validate_preferences(
        location="delhi",
        budget="medium",
        cuisine="north indian",
        min_rating="4.0",
        extra_preferences="family-friendly",
    )
    assert prefs.location == "delhi"

    # 3. Filter
    candidates = filter_restaurants(df, prefs, max_results=20)
    assert isinstance(candidates, list)
    assert len(candidates) >= 1

    # 4. Build prompts
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(prefs, candidates)
    assert "delhi" in user_prompt
    assert "family-friendly" in user_prompt

    # 5. LLM call
    client = GroqClient(api_key="test_key")
    raw_response = client.generate_recommendations(system_prompt, user_prompt)
    assert raw_response == MOCK_LLM_RESPONSE

    # 6. Parse
    recommendations = parse_llm_response(raw_response)
    assert isinstance(recommendations, list)
    assert len(recommendations) == 3
    assert recommendations[0]["rank"] == 1
    assert recommendations[0]["name"] == "Spice Garden"


@patch("pandas.read_parquet")
def test_unknown_city_raises_no_results(mock_read_parquet, mock_datasets_module):
    """Searching in a city with no data should raise NoResultsError."""
    from src.data.ingestion import load_and_preprocess
    from src.filters.preferences import validate_preferences
    from src.filters.engine import filter_restaurants, NoResultsError

    mock_datasets_module.load_dataset.return_value = Mock(
        to_pandas=lambda: MOCK_DATASET.copy()
    )
    mock_read_parquet.side_effect = FileNotFoundError

    df = load_and_preprocess(cache_path=None)
    prefs = validate_preferences(
        location="timbuktu",
        budget="medium",
        cuisine="",
        min_rating="0",
        extra_preferences="",
    )
    with pytest.raises(NoResultsError):
        filter_restaurants(df, prefs)


@patch("pandas.read_parquet")
def test_sparse_city_triggers_relaxation(mock_read_parquet, mock_datasets_module):
    """A high min_rating with sparse data should trigger relaxation and still return results."""
    from src.data.ingestion import load_and_preprocess
    from src.filters.preferences import validate_preferences
    from src.filters.engine import filter_restaurants

    mock_datasets_module.load_dataset.return_value = Mock(
        to_pandas=lambda: MOCK_DATASET.copy()
    )
    mock_read_parquet.side_effect = FileNotFoundError

    df = load_and_preprocess(cache_path=None)
    # Set an impossible min rating — no place has 5.0 — so relaxation must kick in
    prefs = validate_preferences(
        location="delhi",
        budget="medium",
        cuisine="",
        min_rating="5.0",
        extra_preferences="",
    )
    # Relaxation should find results (at least 1)
    results = filter_restaurants(df, prefs)
    assert len(results) >= 1


@patch("pandas.read_parquet")
@patch("src.groq_client.client.groq.Groq")
def test_groq_unavailable_raises_error(mock_groq_class, mock_read_parquet):
    """If Groq API is completely unavailable, the client should raise after retries."""
    import groq
    from src.groq_client.client import GroqClient
    from src.groq_client.exceptions import ApiRateLimitError

    mock_groq_instance = Mock()
    mock_groq_instance.chat.completions.create.side_effect = groq.RateLimitError(
        "Rate limit", response=Mock(), body=None
    )
    mock_groq_class.return_value = mock_groq_instance

    client = GroqClient(api_key="test_key")

    with patch("time.sleep", return_value=None):
        with pytest.raises(ApiRateLimitError):
            client.generate_recommendations("system", "user")


def test_pipeline_handles_zero_min_rating():
    """min_rating=0 should be valid and return all restaurants regardless of rating."""
    from src.filters.preferences import validate_preferences

    prefs = validate_preferences(
        location="delhi",
        budget="high",
        cuisine="",
        min_rating="0",
        extra_preferences="",
    )
    assert prefs.min_rating == 0.0


def test_pipeline_handles_empty_extra_preferences():
    """Empty extra_preferences should still produce a valid UserPreferences object."""
    from src.filters.preferences import validate_preferences

    prefs = validate_preferences(
        location="delhi",
        budget="medium",
        cuisine="",
        min_rating="4.0",
        extra_preferences="",
    )
    assert prefs.extra_preferences is None
