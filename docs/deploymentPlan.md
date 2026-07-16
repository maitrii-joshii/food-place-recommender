# Streamlit Deployment Plan

This document outlines the steps required to adapt and deploy the Food Recommender project onto [Streamlit Community Cloud](https://streamlit.io/cloud).

## 1. Code & Architecture Adaptations

Since the project currently has a CLI interface (`main.py`) and a FastAPI web interface (`server.py`), we need to build a Streamlit-specific frontend that leverages our existing core logic in `src/`.

### Required Changes:
*   **Create `app.py` (or `streamlit_app.py`)**: This will be the main entry point for Streamlit. It will handle the UI (inputs for location, budget, cuisine, etc.) and call the existing functions in `src/`:
    *   `src.data.load_and_preprocess` (with `@st.cache_data` for performance)
    *   `src.filters.preferences.validate_preferences`
    *   `src.filters.filter_restaurants`
    *   `src.prompt.build_system_prompt` and `src.prompt.build_user_prompt`
    *   `src.groq_client.GroqClient.generate_recommendations`
    *   `src.formatter.parse_llm_response`
*   **Update Dependencies**: Add `streamlit` to `requirements.txt`. (Ensure `fastapi` and `uvicorn` are either kept if we want to maintain the API, or removed if Streamlit is the sole target).

## 2. Repository Preparation

Streamlit Community Cloud deploys directly from GitHub.

*   Ensure the code is pushed to a GitHub repository (public or private).
*   Ensure `requirements.txt` is up-to-date and at the root of the repository.
*   Ensure `.gitignore` is correctly configured to ignore `venv/`, `__pycache__/`, `.env`, and the local `zomato_cache.parquet` file (Streamlit will re-download/cache on its own server).

## 3. Deployment Steps on Streamlit Cloud

1.  **Sign in**: Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
2.  **New App**: Click the **"New app"** button.
3.  **Select Repository**: Choose the GitHub repository where the project is hosted.
4.  **Branch and File path**: Select the appropriate branch (e.g., `main`) and set the Main file path to the newly created Streamlit script (e.g., `app.py`).
5.  **Configure Secrets (Crucial)**:
    *   Before clicking "Deploy", click on **"Advanced settings..."**.
    *   Under the **"Secrets"** section, paste the Groq API Key and Model configuration just like in the `.env` file:
        ```toml
        GROQ_API_KEY = "gsk_your_actual_key_here"
        GROQ_MODEL = "llama3-8b-8192"
        ```
    *   *Streamlit will automatically load these as environment variables.*
6.  **Deploy**: Click **"Deploy!"**. Streamlit will provision a container, install dependencies from `requirements.txt`, and launch the app.

## 4. Continuous Integration

*   **Automatic Updates**: Any future pushes to the connected GitHub branch will automatically trigger a rebuild and redeployment of the Streamlit app.
*   **Caching**: We will use Streamlit's `@st.cache_data` on the dataset loading function to ensure the ~10MB Hugging Face dataset is only downloaded once per container lifecycle, mimicking our current Parquet caching strategy but optimized for Streamlit's environment.
