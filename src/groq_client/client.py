import os
import logging
import time
from typing import Optional
from dotenv import load_dotenv
import groq

from .exceptions import (
    ConfigError,
    ApiTimeoutError,
    ApiRateLimitError,
    ModelUnavailableError,
)

logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()


class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if not api_key:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key or api_key == "your_key_here":
                try:
                    import streamlit as st

                    if "GROQ_API_KEY" in st.secrets:
                        api_key = st.secrets["GROQ_API_KEY"]
                except Exception:
                    pass

        self.api_key = api_key
        if not self.api_key or self.api_key == "your_key_here":
            raise ConfigError(
                "Invalid or missing GROQ_API_KEY. Please check your .env file or Streamlit secrets."
            )

        if not model:
            model = os.environ.get("GROQ_MODEL")
            if not model:
                try:
                    import streamlit as st

                    if "GROQ_MODEL" in st.secrets:
                        model = st.secrets["GROQ_MODEL"]
                except Exception:
                    pass

        self.model = model or "openai/gpt-oss-120b"
        self.client = groq.Groq(api_key=self.api_key)

    def generate_recommendations(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends the prompts to the Groq API and returns the raw string response.
        Handles rate limits and timeouts with exponential backoff.
        """
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"},
                    timeout=30.0,  # 30 second timeout
                )
                latency = time.time() - start_time
                logger.debug(f"Groq API call succeeded in {latency:.2f}s")

                content = completion.choices[0].message.content
                if not content:
                    logger.warning("Groq API returned empty response content.")
                    return ""
                return content

            except groq.RateLimitError as e:
                if attempt == max_retries:
                    logger.error(f"Rate limit exhausted after {max_retries} retries.")
                    raise ApiRateLimitError("Groq API rate limit exceeded.") from e

                delay = base_delay * (2**attempt)
                logger.warning(f"Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)

            except groq.APITimeoutError as e:
                if attempt == 1:  # Retry once for timeouts
                    logger.error("Groq API timeout retries exhausted.")
                    raise ApiTimeoutError("Groq API request timed out.") from e
                logger.warning("Groq API request timed out. Retrying...")
                time.sleep(2)

            except groq.NotFoundError as e:
                # If model is not found, try fallback if we are on the primary model
                if self.model == "llama-3.1-8b-instant":
                    logger.warning(
                        f"Model {self.model} not found, falling back to openai/gpt-oss-120b."
                    )
                    self.model = "openai/gpt-oss-120b"
                else:
                    raise ModelUnavailableError(
                        f"Model {self.model} is unavailable."
                    ) from e

            except Exception as e:
                logger.error(f"Unexpected Groq API error: {e}")
                raise
