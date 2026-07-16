from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class UserPreferences:
    location: str
    budget: str
    budget_ceiling: int
    cuisine: Optional[str]
    min_rating: float
    extra_preferences: Optional[str]


BUDGET_MAPPING: Dict[str, int] = {"low": 300, "medium": 700, "high": 9999}


def validate_preferences(
    location: str, budget: str, cuisine: str, min_rating: str, extra_preferences: str
) -> UserPreferences:
    """
    Validates and normalizes raw string inputs into a UserPreferences object.
    Raises ValueError on invalid inputs.
    """
    # 1. Location
    loc_clean = location.strip().lower()
    if not loc_clean:
        raise ValueError("Location cannot be empty.")

    # 2. Budget
    budget_clean = budget.strip().lower()
    if budget_clean not in BUDGET_MAPPING:
        raise ValueError(
            f"Invalid budget: '{budget}'. Allowed values are: 'low', 'medium', 'high'."
        )
    budget_ceiling = BUDGET_MAPPING[budget_clean]

    # 3. Cuisine
    cuisine_clean = cuisine.strip().lower()
    if not cuisine_clean:
        cuisine_clean = None

    # 4. Minimum Rating
    try:
        rating_float = float(min_rating.strip() or 0.0)
    except ValueError:
        raise ValueError(f"Invalid minimum rating: '{min_rating}'. Must be a number.")

    # Clamp rating between 0.0 and 5.0
    rating_float = max(0.0, min(rating_float, 5.0))

    # 5. Extra Preferences
    extra_clean = extra_preferences.strip()
    if not extra_clean or extra_clean.lower() == "none":
        extra_clean = None
    elif len(extra_clean) > 300:
        extra_clean = extra_clean[:300]

    return UserPreferences(
        location=loc_clean,
        budget=budget_clean,
        budget_ceiling=budget_ceiling,
        cuisine=cuisine_clean,
        min_rating=rating_float,
        extra_preferences=extra_clean,
    )
