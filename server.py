import os
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.data import load_and_preprocess
from src.filters import filter_restaurants, NoResultsError
from src.filters.preferences import validate_preferences
from src.prompt import build_system_prompt, build_user_prompt, NoCandidatesError
from src.groq_client import GroqClient, GroqClientError
from src.formatter import parse_llm_response, FormatterError

# Configure minimal logging for the backend
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="Food Recommender API")

# Global dependencies
df = None
llm_client = None


@app.on_event("startup")
async def startup_event():
    global df, llm_client
    logger.info("Initializing Groq client...")
    try:
        llm_client = GroqClient()
    except GroqClientError as e:
        logger.error(f"Failed to initialize GroqClient: {e}")
        # Not exiting so the app still runs and returns 500s on the API,
        # or we could exit here. We'll leave it to fail gracefully on API calls.

    logger.info("Loading dataset...")
    df = load_and_preprocess()
    logger.info("Dataset loaded successfully.")


class RecommendationRequest(BaseModel):
    location: str
    budget: str
    cuisine: Optional[str] = ""
    min_rating: str = "0"
    extra_preferences: Optional[str] = ""


@app.get("/api/metadata")
async def get_metadata():
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded yet")

    cities = sorted(df["location"].dropna().unique().tolist())
    all_cuisines = set(c for sublist in df["cuisines"].dropna() for c in sublist)
    cuisines = sorted(list(all_cuisines))

    return {"cities": cities, "cuisines": cuisines}


@app.post("/api/recommend")
async def get_recommendations(req: RecommendationRequest):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded yet")
    if llm_client is None:
        raise HTTPException(
            status_code=500,
            detail="Groq API client not initialized. Check your API key.",
        )

    try:
        # 1. Validate Preferences
        prefs = validate_preferences(
            location=req.location,
            budget=req.budget,
            cuisine=req.cuisine,
            min_rating=req.min_rating,
            extra_preferences=req.extra_preferences,
        )

        # 2. Filter Restaurants
        try:
            candidates = filter_restaurants(df, prefs, max_results=20)
        except NoResultsError as e:
            return JSONResponse(status_code=404, content={"detail": str(e)})

        # 3. Build Prompts
        system_prompt = build_system_prompt()
        try:
            user_prompt = build_user_prompt(prefs, candidates)
        except NoCandidatesError as e:
            return JSONResponse(status_code=404, content={"detail": str(e)})

        # 4. Generate Recommendations via LLM
        raw_response = llm_client.generate_recommendations(system_prompt, user_prompt)

        # 5. Parse
        try:
            parsed_data = parse_llm_response(raw_response)
        except FormatterError:
            # Fallback to returning raw if parsing fails
            parsed_data = [{"name": "Result", "explanation": raw_response}]

        return {"recommendations": parsed_data}

    except Exception as e:
        logger.exception("Error processing recommendation request")
        raise HTTPException(status_code=500, detail=str(e))


# Mount the static files for the frontend.
# The 'html=True' argument makes it serve index.html at the root automatically.
os.makedirs("public", exist_ok=True)
app.mount("/", StaticFiles(directory="public", html=True), name="public")
