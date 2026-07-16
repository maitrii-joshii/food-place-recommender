import logging
import re
import time
from typing import Optional, List, Union
import pandas as pd
from .exceptions import SchemaError, DatasetLoadError, EmptyDatasetError

# Configure logger for this module
logger = logging.getLogger(__name__)

# The dataset repository on Hugging Face
DATASET_REPO = "ManikaSaini/zomato-restaurant-recommendation"

# We only care about these columns at the end of preprocessing
REQUIRED_OUTPUT_COLUMNS = ["name", "location", "cuisines", "cost", "rating"]


def _normalize_cost(cost_val: Union[str, int, float, None]) -> Optional[int]:
    """Parse string cost fields (e.g., '₹300 for two', '1,200') to integer."""
    if pd.isna(cost_val) or cost_val is None:
        return None
    cost_str = str(cost_val).replace(",", "")
    match = re.search(r"\d+", cost_str)
    if match:
        return int(match.group())
    return None


def _normalize_rating(rating_val: Union[str, int, float, None]) -> Optional[float]:
    """Parse rating strings to float. Handle 'NEW', '-', and missing as None."""
    if pd.isna(rating_val) or rating_val is None:
        return None
    val_str = str(rating_val).strip().upper()
    if val_str in ("NEW", "-", ""):
        return None
    try:
        # Some ratings might be like "4.2/5", we just want the float part.
        match = re.search(r"^(\d+(\.\d+)?)", val_str)
        if match:
            return float(match.group(1))
    except ValueError:
        pass
    return None


def _normalize_location(loc_val: Union[str, None]) -> Optional[str]:
    """Lowercase and strip whitespace. Can also be extended to map known aliases."""
    if pd.isna(loc_val) or loc_val is None:
        return None
    return str(loc_val).strip().lower()


def _normalize_cuisines(cuisine_val: Union[str, None]) -> Optional[List[str]]:
    """Lowercase and split multi-cuisine strings into a list."""
    if pd.isna(cuisine_val) or cuisine_val is None:
        return None
    val_str = str(cuisine_val)
    if not val_str.strip():
        return None
    # Split by comma, strip whitespace, and lower
    return [c.strip().lower() for c in val_str.split(",") if c.strip()]


def load_and_preprocess(
    cache_path: str = "zomato_cache.parquet", force_reload: bool = False
) -> pd.DataFrame:
    """
    Load the Zomato dataset from Hugging Face or local cache,
    preprocess the data, and return a clean DataFrame.
    """
    start_time = time.time()

    if not force_reload and cache_path:
        try:
            df = pd.read_parquet(cache_path)
            logger.info(f"Loaded {len(df)} rows from cache at {cache_path}.")
            return df
        except (FileNotFoundError, Exception) as e:
            logger.debug(
                f"Cache miss or error loading cache: {e}. Falling back to Hugging Face download."
            )

    # 1. Download dataset with retry
    retries = 1
    dataset = None
    for attempt in range(retries + 1):
        try:
            logger.info(
                f"Downloading dataset from Hugging Face: {DATASET_REPO} (Attempt {attempt + 1})"
            )
            from datasets import load_dataset

            dataset = load_dataset(DATASET_REPO, split="train")
            break
        except Exception as e:
            if attempt == retries:
                logger.error("Failed to load dataset after retries.")
                raise DatasetLoadError(
                    f"Could not load dataset {DATASET_REPO}. Check your internet connection. Detail: {str(e)}"
                )
            logger.warning(f"Download failed: {e}. Retrying...")
            time.sleep(2)

    df = dataset.to_pandas()

    if df.empty:
        raise EmptyDatasetError(
            "Dataset appears to be empty after loading from source."
        )

    # 2. Schema validation
    # Actual columns from ManikaSaini/zomato-restaurant-recommendation:
    # ['url', 'address', 'name', 'online_order', 'book_table', 'rate', 'votes',
    #  'phone', 'location', 'rest_type', 'dish_liked', 'cuisines',
    #  'approx_cost(for two people)', 'reviews_list', 'menu_item',
    #  'listed_in(type)', 'listed_in(city)']
    # We map them to our internal standardized names.
    column_mapping = {
        "rate": "rating",
        "approx_cost(for two people)": "cost",
        # 'name', 'location', 'cuisines' already have the correct names
    }

    # Rename matching columns
    df.rename(columns=column_mapping, inplace=True)

    # Check if required columns exist
    missing_cols = set(REQUIRED_OUTPUT_COLUMNS) - set(df.columns)
    if missing_cols:
        raise SchemaError(
            f"Dataset is missing required columns: {missing_cols}. Found: {list(df.columns)}"
        )

    initial_count = len(df)

    # 3. Apply normalization
    df["cost"] = df["cost"].apply(_normalize_cost)
    df["rating"] = df["rating"].apply(_normalize_rating)
    df["location"] = df["location"].apply(_normalize_location)
    df["cuisines"] = df["cuisines"].apply(_normalize_cuisines)

    # Keep only required columns
    df = df[REQUIRED_OUTPUT_COLUMNS]

    # 4. Drop invalid rows
    # Drop where cost is None
    df = df.dropna(subset=["cost"])
    # Drop where cuisines is None (or empty list)
    df = df[df["cuisines"].notnull() & (df["cuisines"].str.len() > 0)]
    # Drop where location is None
    df = df.dropna(subset=["location"])
    # Drop where name is None
    df = df.dropna(subset=["name"])

    # 5. Deduplicate
    df = df.drop_duplicates(subset=["name", "location"])

    final_count = len(df)
    dropped_count = initial_count - final_count

    if df.empty:
        raise EmptyDatasetError("Dataset is empty after dropping invalid rows.")

    logger.info(
        f"Data preprocessing complete. Dropped {dropped_count} invalid/duplicate rows. Final count: {final_count}"
    )

    # Fastparquet cannot save a column containing lists (cuisines). Pyarrow handles it fine.
    # However, to avoid issues, we can save it via pyarrow engine if available, or just not cache cuisines as lists natively if there's an issue.
    # With pandas + pyarrow, caching lists to parquet is standard.
    if cache_path:
        try:
            df.to_parquet(cache_path, engine="pyarrow")
            logger.info(f"Cached preprocessed data to {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to cache dataset to parquet: {e}")

    # Summary
    logger.info(
        f"Data summary: {final_count} rows, {df['location'].nunique()} cities, {df['cuisines'].explode().nunique()} unique cuisines."
    )

    elapsed = time.time() - start_time
    logger.debug(f"Data ingestion took {elapsed:.2f} seconds.")

    return df
