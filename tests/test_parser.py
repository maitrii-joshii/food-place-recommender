import pytest
from src.formatter.parser import parse_llm_response, _extract_json_block
from src.formatter.exceptions import EmptyResponseError, SchemaValidationError


def test_extract_json_block_markdown():
    text = 'Here are your recs:\n```json\n{"recommendations": []}\n```\nEnjoy!'
    extracted = _extract_json_block(text)
    assert extracted == '{"recommendations": []}'


def test_extract_json_block_braces():
    text = 'Sure thing! {"recommendations": []} Have a great day!'
    extracted = _extract_json_block(text)
    assert extracted == '{"recommendations": []}'


def test_parse_valid_response():
    raw = """```json
    {
        "recommendations": [
            {"rank": 1, "name": "Place A", "explanation": "Good food."},
            {"rank": 2, "name": "Place B", "explanation": "Nice vibe."}
        ]
    }
    ```"""
    parsed = parse_llm_response(raw)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]["name"] == "Place A"
    assert parsed[1]["rank"] == 2


def test_parse_invalid_json_fallback():
    # Structurally broken JSON
    raw = '```json\n { "recommendations": [ { "name": "Broken" ] } \n```'
    parsed = parse_llm_response(raw)
    # Should fallback to raw string
    assert isinstance(parsed, str)
    assert "Broken" in parsed


def test_empty_response():
    with pytest.raises(EmptyResponseError):
        parse_llm_response("   ")


def test_missing_recommendations_key():
    raw = '{"recs": [{"name": "A"}]}'
    with pytest.raises(
        SchemaValidationError, match="missing the required 'recommendations' key"
    ):
        parse_llm_response(raw)


def test_invalid_schema_skipping():
    # One valid, one missing 'name', one not a dict
    raw = """{
        "recommendations": [
            {"rank": 1, "name": "Valid", "explanation": "Valid"},
            {"rank": 2, "explanation": "Missing name"},
            "Not a dict at all"
        ]
    }"""
    parsed = parse_llm_response(raw)
    # Should only return the valid one
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Valid"


def test_all_invalid_schema_fallback():
    # If all items are skipped, it returns the raw string as fallback
    raw = """{
        "recommendations": [
            {"rank": 1, "explanation": "Missing name"}
        ]
    }"""
    parsed = parse_llm_response(raw)
    assert isinstance(parsed, str)
    assert "Missing name" in parsed
