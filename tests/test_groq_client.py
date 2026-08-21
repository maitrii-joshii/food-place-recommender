import pytest
import os
from unittest.mock import patch, Mock
import groq
from src.groq_client.client import GroqClient
from src.groq_client.exceptions import (
    ConfigError,
    ApiRateLimitError,
    ApiTimeoutError,
    ModelUnavailableError,
)


def test_missing_api_key():
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ConfigError):
            GroqClient(api_key=None)


def test_generate_recommendations_success():
    client = GroqClient(api_key="test_key")

    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(content='{"recommendations": []}'))]

    with patch.object(
        client.client.chat.completions, "create", return_value=mock_completion
    ) as mock_create:
        response = client.generate_recommendations("sys", "user")
        assert response == '{"recommendations": []}'
        mock_create.assert_called_once()


def test_rate_limit_retry():
    client = GroqClient(api_key="test_key")

    # Fail once with RateLimitError, then succeed
    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(content='{"success": true}'))]

    # We patch time.sleep to avoid actually waiting during tests
    with patch("time.sleep", return_value=None):
        with patch.object(
            client.client.chat.completions,
            "create",
            side_effect=[
                groq.RateLimitError("Rate limit", response=Mock(), body=None),
                mock_completion,
            ],
        ) as mock_create:
            response = client.generate_recommendations("sys", "user")
            assert response == '{"success": true}'
            assert mock_create.call_count == 2


def test_timeout_retry():
    client = GroqClient(api_key="test_key")

    with patch("time.sleep", return_value=None):
        with patch.object(
            client.client.chat.completions,
            "create",
            side_effect=groq.APITimeoutError(request=Mock()),
        ) as mock_create:
            with pytest.raises(ApiTimeoutError):
                client.generate_recommendations("sys", "user")
            assert mock_create.call_count == 2  # Initial + 1 retry


def test_model_fallback():
    client = GroqClient(api_key="test_key", model="openai/gpt-oss-120b")

    mock_completion = Mock()
    mock_completion.choices = [Mock(message=Mock(content='{"fallback": true}'))]

    with patch("time.sleep", return_value=None):
        with patch.object(
            client.client.chat.completions,
            "create",
            side_effect=[
                groq.NotFoundError("Model not found", response=Mock(), body=None),
                mock_completion,
            ],
        ) as mock_create:
            response = client.generate_recommendations("sys", "user")
            assert response == '{"fallback": true}'
            assert mock_create.call_count == 2
            assert client.model == "qwen/qwen3.6-27b"
