# Implementation Plan: AI-Powered Food Place Recommender

## Overview

This document outlines the phase-wise implementation plan for the AI-powered food place recommender. The plan is derived from the project context and the layered pipeline architecture. Each phase builds on the previous one, enabling incremental testing and delivery.

---

## Phases at a Glance

| Phase | Name | Focus | Deliverable |
|---|---|---|---|
| **1** | Project Setup & Environment | Tooling, dependencies, project skeleton | Runnable empty project |
| **2** | Data Ingestion & Preprocessing | Load and clean the Zomato dataset | Clean, queryable DataFrame |
| **3** | User Input & Preference Validation | Collect and normalize user preferences | `UserPreferences` object |
| **4** | Filtering Engine | Hard-constraint restaurant shortlisting | Candidate list |
| **5** | Groq Integration & Prompt Builder | Prompt design and Groq API wiring | LLM-ranked recommendations |
| **6** | Response Formatter & Output Display | Parse Groq output and render results | Polished CLI/UI output |
| **7** | End-to-End Testing & Hardening | Integration tests, edge cases, fallbacks | Production-ready pipeline |
| **8** | Future Enhancements (Optional) | Vector search, multi-turn, feedback loop | Extended capabilities |

---

## Phase 1: Project Setup & Environment

### Goal
Establish the project structure, dependencies, and development environment so every subsequent phase has a solid foundation to build on.

### Tasks
- [ ] Initialize Git repository and set up `.gitignore`
- [ ] Create the project directory structure:
  ```
  food-place-recommender/
  ├── docs/
  ├── src/
  │   ├── data/           # Data ingestion & preprocessing
  │   ├── filters/        # Filtering engine
  │   ├── prompt/         # Prompt builder
  │   ├── groq_client/    # Groq API integration
  │   ├── formatter/      # Response formatter
  │   └── ui/             # Output display (CLI or Web)
  ├── tests/
  ├── .env.example
  ├── requirements.txt
  └── main.py
  ```
- [ ] Create `requirements.txt` with core dependencies:
  - `datasets` — Hugging Face dataset loading
  - `pandas` — Data processing
  - `groq` — Groq Python SDK
  - `python-dotenv` — Environment variable management
  - `rich` or `tabulate` — CLI output formatting
- [ ] Set up `.env.example` with `GROQ_API_KEY=your_key_here`
- [ ] Set up virtual environment and install dependencies
- [ ] Write a smoke-test `main.py` that prints "Pipeline ready"

### Acceptance Criteria
- Project installs cleanly with `pip install -r requirements.txt`
- Running `python main.py` succeeds without errors

---

## Phase 2: Data Ingestion & Preprocessing

### Goal
Load the Zomato dataset from Hugging Face, clean it, and expose it as a normalized, queryable structure for the filtering engine.

### Architecture Layer
→ **Data Ingestion & Storage Layer** (`src/data/`)

### Tasks
- [ ] Load the dataset using Hugging Face `datasets` library:
  ```python
  from datasets import load_dataset
  ds = load_dataset("ManikaSaini/zomato-restaurant-recommendation")
  ```
- [ ] Convert to a Pandas DataFrame
- [ ] Implement preprocessing pipeline:
  - [ ] **Cost normalization**: Parse string cost fields (e.g., `"₹300 for two"`) → integer
  - [ ] **Rating normalization**: Parse rating strings to `float`; handle `"NEW"` / `NaN` → `None`
  - [ ] **Location standardization**: Lowercase + strip whitespace; map known aliases
  - [ ] **Cuisine normalization**: Lowercase; split multi-cuisine strings into a list
  - [ ] **Column pruning**: Retain only `name`, `location`, `cuisines`, `cost`, `rating`
- [ ] Write unit tests for each preprocessing function with edge-case inputs
- [ ] Expose a `load_and_preprocess()` function that returns the clean DataFrame

### Acceptance Criteria
- `load_and_preprocess()` returns a DataFrame with no null values in critical fields
- All cost values are integers; all ratings are floats or `None`
- Unit tests pass for preprocessing functions

---

## Phase 3: User Input & Preference Validation

### Goal
Provide a clean interface for collecting user preferences and validate/normalize them into a typed `UserPreferences` object consumed by the rest of the pipeline.

### Architecture Layer
→ **User Interface Layer** + **Preference Validator** (`src/ui/` + `src/filters/`)

### Tasks
- [ ] Define the `UserPreferences` dataclass / Pydantic model:
  ```python
  @dataclass
  class UserPreferences:
      location: str
      budget: str          # "low" | "medium" | "high"
      budget_ceiling: int  # derived: low=300, medium=700, high=9999
      cuisine: str
      min_rating: float
      extra_preferences: str
  ```
- [ ] Implement budget → cost ceiling mapping:
  - `low` → ≤ ₹300
  - `medium` → ≤ ₹700
  - `high` → no upper limit
- [ ] Implement `collect_preferences()` for CLI (using `input()` prompts with sensible defaults)
- [ ] Implement `validate_preferences(raw_input) -> UserPreferences`:
  - Normalize `location` and `cuisine` (lowercase, strip)
  - Validate `budget` is one of the accepted enum values
  - Clamp `min_rating` to `[0.0, 5.0]`
  - Raise descriptive `ValueError` for invalid inputs
- [ ] Write unit tests for validation logic

### Acceptance Criteria
- CLI successfully collects all 5 preference fields
- Invalid inputs (e.g., bad budget value, rating > 5) raise clear errors
- `UserPreferences` object is correctly populated for all valid inputs

---

## Phase 4: Filtering Engine

### Goal
Implement the hard-constraint filtering pipeline that takes the clean dataset and user preferences, and returns a relevant shortlist of candidate restaurants for Groq to reason over.

### Architecture Layer
→ **Filtering Engine** (`src/filters/`)

### Tasks
- [ ] Implement the sequential filter pipeline:
  1. **Location filter**: `df[df['location'] == preferences.location]`
  2. **Cuisine filter**: Rows where `cuisines` list overlaps `preferences.cuisine` (exact first; fuzzy fallback using `difflib` or `fuzzywuzzy`)
  3. **Budget filter**: `df[df['cost'] <= preferences.budget_ceiling]`
  4. **Rating filter**: `df[df['rating'] >= preferences.min_rating]` (exclude `None` ratings)
- [ ] Implement fallback relaxation strategy:
  - If result count < 3: relax `min_rating` by `–0.5` and retry
  - If still < 3: relax budget by one tier and retry
  - Log each relaxation step so the user can be informed
- [ ] Cap output at **N = 20** candidates (sorted by rating descending)
- [ ] Expose `filter_restaurants(df, preferences) -> List[dict]`
- [ ] Write unit tests covering:
  - Normal filtering path
  - Fuzzy cuisine matching
  - Fallback relaxation triggering
  - Empty result edge case

### Acceptance Criteria
- Filter returns at least 3 results for any valid city in the dataset
- Fuzzy cuisine matching handles common typos/variants
- Fallback relaxation is triggered and logged correctly

---

## Phase 5: Groq Integration & Prompt Builder

### Goal
Design the prompt template, integrate the Groq API, and wire the candidate list + user preferences into a Groq inference call that returns ranked, explained recommendations.

### Architecture Layer
→ **Prompt Builder** + **Recommendation Engine (Groq)** (`src/prompt/` + `src/groq_client/`)

### Tasks

#### 5a: Groq API Client
- [ ] Install and configure the `groq` Python SDK
- [ ] Load `GROQ_API_KEY` from `.env` using `python-dotenv`
- [ ] Create `GroqClient` wrapper:
  - Accepts a prompt string
  - Calls `client.chat.completions.create(model="llama3-8b-8192", ...)`
  - Returns raw response text
- [ ] Handle API errors: rate limits, timeouts, malformed responses

#### 5b: Prompt Builder
- [ ] Implement `build_system_prompt()` — static system instructions
- [ ] Implement `format_candidates(candidates: List[dict]) -> str` — formats the shortlist into a structured string
- [ ] Implement `build_user_prompt(preferences, candidates) -> str` using the template:
  ```
  User Preferences:
  - Location: {location}
  - Budget: {budget} (up to ₹{budget_ceiling} for two)
  - Cuisine: {cuisine}
  - Minimum Rating: {min_rating}
  - Additional Notes: {extra_preferences}

  Available Restaurants:
  {formatted_candidates}

  Rank and explain these options. Return a JSON array.
  ```
- [ ] Implement token budget management:
  - Estimate ~100 tokens per candidate
  - Trim candidate list if it would exceed 80% of model context window (8192 tokens for `llama3-8b-8192`)
- [ ] Write prompt unit tests (check prompt contains all required fields)
- [ ] Write integration test: send a mock candidate list to Groq and verify structured JSON response

### Acceptance Criteria
- Groq API call succeeds with a valid API key
- Prompt contains all user preference fields and full candidate list (within token budget)
- Groq returns a parseable JSON array of ranked recommendations

---

## Phase 6: Response Formatter & Output Display

### Goal
Parse and validate Groq's raw output into typed `Recommendation` objects, then render them to the user in a clear, readable format.

### Architecture Layer
→ **Response Formatter** + **Output Display** (`src/formatter/` + `src/ui/`)

### Tasks

#### 6a: Response Formatter
- [ ] Define `Recommendation` dataclass:
  ```python
  @dataclass
  class Recommendation:
      rank: int
      name: str
      cuisine: str
      rating: float
      cost: int
      explanation: str
  ```
- [ ] Implement `parse_groq_response(raw: str) -> List[Recommendation]`:
  - Extract JSON from raw response (handle markdown code fences if present)
  - Validate required fields per item
  - Fall back to a generic explanation if `explanation` is missing
  - Raise `ResponseParseError` for fully unparseable output
- [ ] Write unit tests for parse function with:
  - Valid JSON response
  - JSON wrapped in a markdown code fence
  - Partially malformed response (missing fields)
  - Completely invalid response

#### 6b: Output Display
- [ ] Implement `display_recommendations(recommendations: List[Recommendation])` using `rich` library:
  - Render each recommendation as a styled card with emoji icons
  - Show rank, name, cuisine, rating, cost, and AI explanation
  - Add a brief summary header above all cards
- [ ] Implement graceful display for fallback cases (e.g., "Results relaxed to include lower-rated options")

### Acceptance Criteria
- Full pipeline runs end-to-end from CLI input to displayed results
- Recommendation cards render correctly with all fields populated
- Graceful error messages shown for parse failures

---

## Phase 7: End-to-End Testing & Hardening

### Goal
Ensure the full pipeline is robust, handles real-world edge cases, and is ready for use.

### Tasks

#### Integration Testing
- [ ] Write end-to-end test: pass known preferences → verify top recommendation makes sense
- [ ] Test with cities that have sparse data (few restaurants match) — verify fallback triggers
- [ ] Test with unsupported cities — verify graceful "no results" message
- [ ] Test with Groq API unavailable (mock) — verify error handling

#### Edge Case Hardening
- [ ] Handle dataset download failures (network error on Hugging Face)
- [ ] Handle Groq rate limiting (exponential backoff retry)
- [ ] Handle `min_rating = 0` (return all restaurants regardless of rating)
- [ ] Handle empty `extra_preferences` (system should still work)

#### Code Quality
- [ ] Add logging throughout the pipeline (`logging` module with levels)
- [ ] Add docstrings to all public functions
- [ ] Run `pylint` / `flake8` and fix warnings
- [ ] Update `README.md` with setup instructions and usage examples

### Acceptance Criteria
- All unit and integration tests pass
- Pipeline handles all documented edge cases without crashing
- README clearly explains how to set up and run the project

---

## Phase 8: Future Enhancements (Optional)

These are not required for the initial delivery but are documented here for future sprints.

| Enhancement | Description | Complexity |
|---|---|---|
| **Vector Search** | Embed restaurant descriptions using sentence transformers; use FAISS/Chroma for semantic similarity search — supports vague queries like "something cozy" | High |
| **Web UI** | Replace CLI with a FastAPI backend + React/Streamlit frontend | Medium |
| **Multi-turn Conversation** | Support follow-up queries: "show me cheaper options", "only vegetarian ones" | Medium |
| **User History** | Persist preferences and past recommendations per user session | Medium |
| **Feedback Loop** | Collect thumbs up/down; use to re-rank or fine-tune prompts over time | High |
| **Caching** | Cache Groq responses for identical preference sets to reduce API calls and latency | Low |

---

## Dependencies Between Phases

```
Phase 1 (Setup)
  └─► Phase 2 (Data Ingestion)
        └─► Phase 3 (User Input)
              └─► Phase 4 (Filtering Engine)
                    └─► Phase 5 (Groq Integration)
                          └─► Phase 6 (Output Display)
                                └─► Phase 7 (Testing & Hardening)
                                      └─► Phase 8 (Optional Enhancements)
```

Each phase must be complete and passing its acceptance criteria before the next phase begins.

---

## Definition of Done

A phase is considered **done** when:
1. All tasks in the phase checklist are marked complete
2. All acceptance criteria are met
3. Unit tests for the phase are written and passing
4. Code is reviewed and committed to the repository
