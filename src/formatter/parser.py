import json
import re
import logging
from typing import List, Dict, Any, Union

from .exceptions import EmptyResponseError, SchemaValidationError

logger = logging.getLogger(__name__)


def _extract_json_block(text: str) -> str:
    """
    Extracts a JSON block from a string, handling markdown formatting
    and conversational conversational prefixes/suffixes.
    """
    # Try to find a markdown json block
    markdown_match = re.search(
        r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE
    )
    if markdown_match:
        return markdown_match.group(1).strip()

    # If no markdown block, try to find the outermost curly braces
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        return brace_match.group(1).strip()

    return text.strip()


def parse_llm_response(raw_response: str) -> Union[List[Dict[str, Any]], str]:
    """
    Parses the raw LLM response.
    Returns a list of recommendation dictionaries if parsing succeeds.
    Returns the raw string as a fallback if JSON parsing fails entirely.
    """
    if not raw_response or not raw_response.strip():
        raise EmptyResponseError("The LLM returned an empty response.")

    extracted_text = _extract_json_block(raw_response)

    try:
        parsed = json.loads(extracted_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Fallback to returning the raw string
        return raw_response

    # Validate schema
    if "recommendations" not in parsed:
        logger.error("JSON missing 'recommendations' key.")
        raise SchemaValidationError(
            "The response JSON is missing the required 'recommendations' key."
        )

    recommendations = parsed["recommendations"]
    if not isinstance(recommendations, list):
        logger.error("'recommendations' key is not a list.")
        raise SchemaValidationError("'recommendations' must be a list of objects.")

    validated = []
    for i, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            logger.warning(f"Recommendation at index {i} is not an object. Skipping.")
            continue

        # Ensure keys exist
        if "name" not in rec or "explanation" not in rec or "rank" not in rec:
            logger.warning(
                f"Recommendation at index {i} is missing required keys. Skipping. Data: {rec}"
            )
            continue

        validated.append(
            {
                "rank": rec["rank"],
                "name": rec["name"],
                "explanation": rec["explanation"],
            }
        )

    if not validated:
        logger.warning(
            "No valid recommendations found after schema validation. Returning raw string."
        )
        return raw_response

    return validated
