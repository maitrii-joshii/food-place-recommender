import pytest
from src.prompt.builder import (
    build_system_prompt,
    build_user_prompt,
    format_candidates,
    NoCandidatesError,
)
from src.filters.preferences import UserPreferences


def test_build_system_prompt():
    prompt = build_system_prompt()
    assert "You are a knowledgeable restaurant recommendation assistant" in prompt
    assert "JSON object" in prompt


def test_format_candidates():
    candidates = [
        {"name": "Place A", "cuisines": ["italian"], "cost": 500, "rating": 4.5},
        {"name": 'Place "B"', "cuisines": [], "cost": 300, "rating": None},
    ]
    formatted = format_candidates(candidates)

    assert "Place A" in formatted
    assert "Place 'B'" in formatted  # Check sanitization of quotes
    assert "Cuisines: italian" in formatted
    assert "Cost: ₹500" in formatted


def test_no_candidates():
    with pytest.raises(NoCandidatesError):
        format_candidates([])


def test_build_user_prompt():
    prefs = UserPreferences(
        location="delhi",
        budget="medium",
        budget_ceiling=700,
        cuisine="italian",
        min_rating=4.0,
        extra_preferences="outdoor seating \n test",
    )
    candidates = [
        {"name": "Place A", "cuisines": ["italian"], "cost": 500, "rating": 4.5}
    ]

    prompt = build_user_prompt(prefs, candidates)

    assert "delhi" in prompt
    assert "medium" in prompt
    assert "700" in prompt
    assert "italian" in prompt
    assert "4.0" in prompt
    assert "outdoor seating   test" in prompt  # newline sanitized to space
    assert "Place A" in prompt


def test_token_budget_trimming(monkeypatch):
    # Mock MAX_TOKENS to simulate a small token budget
    import src.prompt.builder as builder

    monkeypatch.setattr(
        builder, "MAX_TOKENS", 300
    )  # Only allows 300 / 120 = 2 candidates

    candidates = [{"name": f"Place {i}"} for i in range(5)]

    formatted = builder.format_candidates(candidates)

    # Should only contain Place 0 and Place 1
    assert "Place 0" in formatted
    assert "Place 1" in formatted
    assert "Place 2" not in formatted
    assert "Place 3" not in formatted
