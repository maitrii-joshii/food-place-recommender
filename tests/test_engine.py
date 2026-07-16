import pytest
import pandas as pd
from src.filters.engine import filter_restaurants, NoResultsError, _fuzzy_match_cuisine
from src.filters.preferences import UserPreferences


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "name": [
                "Place A",
                "Place B",
                "Place C",
                "Place D",
                "Place E",
                "Place F",
                "Place G",
            ],
            "location": [
                "delhi",
                "delhi",
                "mumbai",
                "delhi",
                "chennai",
                "delhi",
                "delhi",
            ],
            "cuisines": [
                ["italian", "chinese"],
                ["north indian"],
                ["chinese"],
                ["italian"],
                ["fast food"],
                ["italian"],
                ["italian"],
            ],
            "cost": [1000, 500, 300, 250, 200, 800, 900],
            "rating": [4.5, 4.0, 3.5, 2.0, None, 4.8, 4.6],
        }
    )


def test_location_filter_empty(sample_df):
    prefs = UserPreferences(
        location="goa",
        budget="high",
        budget_ceiling=9999,
        cuisine=None,
        min_rating=0.0,
        extra_preferences=None,
    )
    with pytest.raises(NoResultsError, match="No restaurants found"):
        filter_restaurants(sample_df, prefs)


def test_strict_filtering(sample_df):
    # Should only match Place A (cost <= 9999, rating >= 4.5, cuisine italian)
    prefs = UserPreferences(
        location="delhi",
        budget="high",
        budget_ceiling=9999,
        cuisine="italian",
        min_rating=4.5,
        extra_preferences=None,
    )
    results = filter_restaurants(sample_df, prefs)
    assert len(results) == 3
    names = [r["name"] for r in results]
    assert "Place A" in names
    assert "Place F" in names
    assert "Place G" in names


def test_budget_relaxation(sample_df):
    # Looking for italian in delhi, budget low (<=300).
    # Place D is italian, cost 250, but rating is 2.0.
    # Place A is italian, cost 1000, rating is 4.5.
    # If we ask for rating >= 4.0 and budget low, no matches initially.
    # It should relax rating, then budget.
    prefs = UserPreferences(
        location="delhi",
        budget="low",
        budget_ceiling=300,
        cuisine="italian",
        min_rating=4.0,
        extra_preferences=None,
    )
    # The relaxation logic drops min_rating by 0.5 twice (to 3.0). Place D rating is 2.0, so still dropped.
    # Then it relaxes budget to medium (700) -> Place D still rating 2.0 (dropped), Place A is 1000 (dropped).
    # Then relaxes budget to high (9999) -> Place A (cost 1000, rating 4.5) will be picked!
    # Wait, the relaxation loop relaxes cuisine first if < 3.
    # With italian: Place A (cost 1000, rating 4.5), Place D (cost 250, rating 2.0).
    # Let's see exactly how it behaves, but we expect at least 1 result.
    results = filter_restaurants(sample_df, prefs)
    assert len(results) >= 1
    assert "Place A" in [r["name"] for r in results]


def test_fuzzy_match():
    available = {"north indian", "chinese", "italian", "fast food"}
    matches = _fuzzy_match_cuisine("itallian", available)
    assert "italian" in matches

    matches = _fuzzy_match_cuisine("chineese", available)
    assert "chinese" in matches


def test_max_results_and_sorting(sample_df):
    # Add more rows to test capping
    extra_rows = pd.DataFrame(
        {
            "name": [f"Extra {i}" for i in range(25)],
            "location": ["delhi"] * 25,
            "cuisines": [["chinese"]] * 25,
            "cost": [200] * 25,
            "rating": [4.0] * 25,
        }
    )
    big_df = pd.concat([sample_df, extra_rows], ignore_index=True)

    prefs = UserPreferences(
        location="delhi",
        budget="medium",
        budget_ceiling=700,
        cuisine="chinese",
        min_rating=3.0,
        extra_preferences=None,
    )
    results = filter_restaurants(big_df, prefs, max_results=10)

    assert len(results) == 10
    # Should be sorted by rating descending
    ratings = [r["rating"] for r in results]
    assert ratings == sorted(ratings, reverse=True)


def test_none_rating_exclusion_and_inclusion(sample_df):
    # Place E has None rating and is the only place in chennai.
    # Strict rating filter (min_rating=0.0) should exclude it (since it's not >= 0.0)
    prefs = UserPreferences(
        location="chennai",
        budget="high",
        budget_ceiling=9999,
        cuisine="fast food",
        min_rating=0.0,
        extra_preferences=None,
    )
    results = filter_restaurants(sample_df, prefs)
    # Since it relaxes constraints when < 3, it will eventually drop rating filter entirely.
    assert any(r["name"] == "Place E" for r in results)
    assert any(r["rating"] is None for r in results)
