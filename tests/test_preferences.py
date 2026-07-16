import pytest
from src.filters.preferences import validate_preferences, UserPreferences


def test_valid_preferences():
    prefs = validate_preferences(
        location="  Delhi ",
        budget="MEDIUM ",
        cuisine=" Italian  ",
        min_rating="4.2",
        extra_preferences=" Outdoor seating ",
    )
    assert prefs.location == "delhi"
    assert prefs.budget == "medium"
    assert prefs.budget_ceiling == 700
    assert prefs.cuisine == "italian"
    assert prefs.min_rating == 4.2
    assert prefs.extra_preferences == "Outdoor seating"


def test_budget_mapping():
    assert validate_preferences("Delhi", "low", "", "4", "").budget_ceiling == 300
    assert validate_preferences("Delhi", "medium", "", "4", "").budget_ceiling == 700
    assert validate_preferences("Delhi", "high", "", "4", "").budget_ceiling == 9999


def test_invalid_budget():
    with pytest.raises(ValueError, match="Invalid budget"):
        validate_preferences("Delhi", "expensive", "", "4", "")


def test_rating_clamping():
    # Above 5.0 -> 5.0
    prefs_high = validate_preferences("Delhi", "low", "", "6.5", "")
    assert prefs_high.min_rating == 5.0

    # Below 0.0 -> 0.0
    prefs_low = validate_preferences("Delhi", "low", "", "-2.0", "")
    assert prefs_low.min_rating == 0.0


def test_invalid_rating():
    with pytest.raises(ValueError, match="Must be a number"):
        validate_preferences("Delhi", "low", "", "four", "")


def test_empty_location():
    with pytest.raises(ValueError, match="Location cannot be empty"):
        validate_preferences("   ", "low", "", "4", "")


def test_empty_cuisine():
    prefs = validate_preferences("Delhi", "low", "   ", "4", "")
    assert prefs.cuisine is None


def test_extra_preferences_handling():
    # Empty string
    prefs_empty = validate_preferences("Delhi", "low", "", "4", "   ")
    assert prefs_empty.extra_preferences is None

    # "None" string
    prefs_none = validate_preferences("Delhi", "low", "", "4", "None")
    assert prefs_none.extra_preferences is None

    # Truncation (> 300 chars)
    long_string = "a" * 400
    prefs_long = validate_preferences("Delhi", "low", "", "4", long_string)
    assert len(prefs_long.extra_preferences) == 300
    assert prefs_long.extra_preferences == "a" * 300
