import logging
import difflib
import pandas as pd
from typing import List, Dict, Any
from .preferences import UserPreferences, BUDGET_MAPPING

logger = logging.getLogger(__name__)


class NoResultsError(Exception):
    """Raised when no restaurants can be found even after relaxations."""

    pass


def _fuzzy_match_cuisine(target: str, available_cuisines: set) -> List[str]:
    """Finds close matches for a cuisine string in the available dataset cuisines."""
    return difflib.get_close_matches(target, available_cuisines, n=3, cutoff=0.6)


def filter_restaurants(
    df: pd.DataFrame, prefs: UserPreferences, max_results: int = 20
) -> List[Dict[str, Any]]:
    """
    Filters the restaurant dataset based on user preferences.
    If the strict filters yield fewer than 3 results, it applies graceful relaxations
    to rating, budget, and cuisine to ensure a reasonable shortlist is returned.
    """
    logger.debug(f"Starting filter pipeline with initial {len(df)} rows.")

    # 1. Location Filter (Hard constraint)
    df_loc = df[df["location"] == prefs.location]
    if df_loc.empty:
        raise NoResultsError(f"No restaurants found in location: '{prefs.location}'.")
    logger.debug(f"After location filter: {len(df_loc)} rows.")

    def apply_filters(
        data: pd.DataFrame,
        cuisine: str = None,
        budget_ceiling: int = None,
        min_rating: float = None,
        ignore_cuisine: bool = False,
    ) -> pd.DataFrame:
        temp = data.copy()

        # Cuisine Filter
        if cuisine and not ignore_cuisine:
            # Check exact or substring match
            exact_mask = temp["cuisines"].apply(
                lambda c_list: any(cuisine in c for c in c_list)
            )
            if not exact_mask.any():
                # Fuzzy fallback
                all_cuisines = set(c for sublist in temp["cuisines"] for c in sublist)
                fuzzy_matches = _fuzzy_match_cuisine(cuisine, all_cuisines)
                if fuzzy_matches:
                    logger.info(
                        f"Cuisine '{cuisine}' not found exactly. Fuzzy matched to: {fuzzy_matches}"
                    )
                    temp = temp[
                        temp["cuisines"].apply(
                            lambda c_list: any(fm in c_list for fm in fuzzy_matches)
                        )
                    ]
                else:
                    logger.info(
                        f"Cuisine '{cuisine}' had no fuzzy matches. Relaxing cuisine filter entirely."
                    )
                    temp = temp[False]  # Force empty so we relax in the outer loop
            else:
                temp = temp[exact_mask]

        # Budget Filter
        if budget_ceiling and prefs.budget != "high":
            temp = temp[temp["cost"] <= budget_ceiling]

        # Rating Filter
        if min_rating is not None and min_rating > 0.0:
            # Only filter by rating when there's an actual minimum threshold.
            # At 0.0, the user has no rating requirement so all restaurants
            # (including unrated ones) are included.
            temp = temp[temp["rating"].notnull() & (temp["rating"] >= min_rating)]

        return temp

    # Baseline strict filtering
    results = apply_filters(
        df_loc,
        cuisine=prefs.cuisine,
        budget_ceiling=prefs.budget_ceiling,
        min_rating=prefs.min_rating,
    )

    # Relaxation Loop
    current_min_rating = prefs.min_rating
    current_budget = prefs.budget
    current_budget_ceiling = prefs.budget_ceiling
    ignore_cuisine = False

    relaxations_applied = []

    # Step 1: We deliberately DO NOT relax the cuisine preference anymore.
    # Users generally prefer fewer results over completely different cuisines.

    # Step 2: Relax rating twice by 0.5
    for _ in range(2):
        if len(results) >= 3:
            break
        if current_min_rating > 0:
            current_min_rating = max(0.0, current_min_rating - 0.5)
            relaxations_applied.append(f"rating_dropped_to_{current_min_rating}")
            logger.info(f"Relaxed filter: Dropped min rating to {current_min_rating}.")
            results = apply_filters(
                df_loc,
                cuisine=prefs.cuisine,
                budget_ceiling=current_budget_ceiling,
                min_rating=current_min_rating,
                ignore_cuisine=ignore_cuisine,
            )

    # Step 3: Relax budget tier if still < 3
    if len(results) < 3:
        if current_budget == "low":
            current_budget = "medium"
            current_budget_ceiling = BUDGET_MAPPING["medium"]
            relaxations_applied.append("budget_relaxed_to_medium")
            logger.info("Relaxed filter: Increased budget to medium.")
            results = apply_filters(
                df_loc,
                cuisine=prefs.cuisine,
                budget_ceiling=current_budget_ceiling,
                min_rating=current_min_rating,
                ignore_cuisine=ignore_cuisine,
            )

        if len(results) < 3 and current_budget == "medium":
            current_budget = "high"
            current_budget_ceiling = BUDGET_MAPPING["high"]
            relaxations_applied.append("budget_relaxed_to_high")
            logger.info("Relaxed filter: Increased budget to high.")
            results = apply_filters(
                df_loc,
                cuisine=prefs.cuisine,
                budget_ceiling=current_budget_ceiling,
                min_rating=current_min_rating,
                ignore_cuisine=ignore_cuisine,
            )

    # Final Step: If still < 3, just drop rating filter completely (which allows None ratings)
    if len(results) < 3:
        logger.info(
            "Relaxed filter: Dropped rating filter completely (including unrated restaurants)."
        )
        relaxations_applied.append("rating_dropped_completely")
        results = apply_filters(
            df_loc,
            cuisine=prefs.cuisine,
            budget_ceiling=current_budget_ceiling,
            min_rating=None,  # Allow None ratings
            ignore_cuisine=ignore_cuisine,
        )

    if results.empty:
        raise NoResultsError("No results found even after relaxing all constraints.")

    logger.debug(
        f"Filtering complete. Final rows: {len(results)}. Relaxations: {relaxations_applied}"
    )

    # Sorting: descending by rating. Pandas handles NaN by putting them at the end if we use na_position='last'
    results = results.sort_values(by="rating", ascending=False, na_position="last")

    # Cap results
    results = results.head(max_results)

    # Convert dataframe to list of dicts. We use astype(object) to ensure Python None instead of NaN.
    # Note: to_dict('records') keeps NaNs as floats. We'll explicitly handle that for JSON compliance downstream.
    final_results = (
        results.astype(object).where(pd.notnull(results), None).to_dict("records")
    )

    return final_results
