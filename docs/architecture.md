# Architecture: AI-Powered Food Place Recommender

## 1. Overview

This document describes the detailed technical architecture of the AI-powered food place recommender. The system follows a **layered pipeline architecture** where each layer has a single well-defined responsibility. Structured data filtering and LLM-based reasoning are intentionally kept separate to ensure accuracy, explainability, and maintainability.

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│         (CLI / Web UI — collects user preferences)          │
└─────────────────────────┬───────────────────────────────────┘
                           │  User Preferences
                           │  (location, budget, cuisine,
                           │   min rating, extra preferences)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PREFERENCE VALIDATOR                        │
│         (Normalize & validate structured inputs)             │
└─────────────────────────┬───────────────────────────────────┘
                           │  Validated Preference Object
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               DATA INGESTION & STORAGE LAYER                 │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Hugging Face Dataset                                │  │
│   │  (ManikaSaini/zomato-restaurant-recommendation)      │  │
│   └────────────────────────┬─────────────────────────────┘  │
│                            │ Raw records                     │
│   ┌────────────────────────▼─────────────────────────────┐  │
│   │  Preprocessing & Normalization                       │  │
│   │  - Parse cost strings → numeric ranges               │  │
│   │  - Normalize cuisine labels                          │  │
│   │  - Map ratings to float                              │  │
│   │  - Standardize city / location names                 │  │
│   └────────────────────────┬─────────────────────────────┘  │
│                            │ Cleaned DataFrame / records     │
└────────────────────────────┼────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   FILTERING ENGINE                           │
│                                                             │
│   Hard Constraint Filters (applied in order):               │
│   1. Location match                                         │
│   2. Cuisine match (exact or fuzzy)                         │
│   3. Budget range filter (cost ≤ budget ceiling)            │
│   4. Minimum rating threshold                               │
│                                                             │
│   Output: shortlist of N candidate restaurants              │
└─────────────────────────┬───────────────────────────────────┘
                           │  Candidate List (structured JSON)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROMPT BUILDER                              │
│                                                             │
│   - Formats candidate restaurants into structured context    │
│   - Injects user's soft preferences (e.g., family-friendly) │
│   - Wraps everything in a system + user prompt template      │
│   - Controls token budget (truncates if candidate list       │
│     exceeds context limit)                                   │
└─────────────────────────┬───────────────────────────────────┘
                           │  Fully-formed LLM Prompt
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               RECOMMENDATION ENGINE (LLM)                    │
│                                                             │
│   - Receives: structured candidate data + user intent        │
│   - Ranks candidates by fit                                  │
│   - Generates a natural language explanation per restaurant  │
│   - Optionally produces a summary of top choices             │
│   - Returns: ranked list with explanations (JSON / text)     │
└─────────────────────────┬───────────────────────────────────┘
                           │  Ranked Recommendations + Explanations
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   RESPONSE FORMATTER                         │
│         (Parse LLM output → display-ready structure)         │
└─────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     OUTPUT DISPLAY                           │
│                                                             │
│   Per recommendation:                                        │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  🍽️  Restaurant Name                                │   │
│   │  🍜  Cuisine Type                                   │   │
│   │  ⭐  Rating                                         │   │
│   │  💰  Estimated Cost                                 │   │
│   │  🤖  AI Explanation                                 │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Breakdown

### 3.1 User Interface Layer

**Responsibility**: Collect and expose user preferences.

| Input Field | Type | Description |
|---|---|---|
| `location` | `string` | City or area (e.g., Delhi, Bangalore) |
| `budget` | `enum` | `low` / `medium` / `high` |
| `cuisine` | `string` | Cuisine preference (e.g., Italian, Chinese) |
| `min_rating` | `float` | Minimum acceptable rating (e.g., 4.0) |
| `extra_preferences` | `string` | Freeform text (e.g., "family-friendly, outdoor seating") |

> This layer is decoupled from the rest of the pipeline — the same backend can serve a CLI, a REST API, or a web frontend.

---

### 3.2 Preference Validator

**Responsibility**: Normalize and validate raw user inputs before they hit the data layer.

- Validates `budget` is one of the accepted enum values
- Converts `budget` enum → cost ceiling: `low ≤ ₹300`, `medium ≤ ₹700`, `high > ₹700`
- Trims and lowercases `location` and `cuisine` for consistent matching
- Clamps `min_rating` to `[0.0, 5.0]`
- Returns a typed `UserPreferences` object

---

### 3.3 Data Ingestion & Storage Layer

**Responsibility**: Load, preprocess, and make the Zomato dataset queryable.

#### Data Source
- **Dataset**: `ManikaSaini/zomato-restaurant-recommendation` on Hugging Face
- **Access**: via `datasets` library (`load_dataset(...)`)

#### Preprocessing Steps
1. **Cost normalization**: Parse string cost fields (e.g., `"₹300 for two"`) into numeric values
2. **Rating normalization**: Parse rating strings to `float`; handle missing/`"NEW"` values gracefully
3. **Location standardization**: Lowercase and strip whitespace; handle aliases (e.g., `"New Delhi"` → `"delhi"`)
4. **Cuisine normalization**: Lowercase; split multi-cuisine entries (e.g., `"North Indian, Chinese"`) into a list
5. **Drop irrelevant columns**: Retain only `name`, `location`, `cuisines`, `cost`, `rating`

#### Storage Strategy
- For **development**: hold the cleaned dataset in-memory as a Pandas DataFrame
- For **production scale**: persist to a lightweight DB (e.g., SQLite or DuckDB) for faster filtered queries

---

### 3.4 Filtering Engine

**Responsibility**: Apply hard-constraint filters to narrow the dataset to a relevant shortlist.

#### Filter Pipeline (applied sequentially)

```
Dataset
  │
  ├─[1] Location Filter   → keep rows where location matches user city
  │
  ├─[2] Cuisine Filter    → keep rows where cuisines overlap user preference
  │                         (exact match first; fuzzy fallback if < 5 results)
  │
  ├─[3] Budget Filter     → keep rows where cost ≤ budget ceiling
  │
  └─[4] Rating Filter     → keep rows where rating ≥ min_rating
          │
          ▼
     Candidate List (up to N restaurants, default N=20)
```

#### Fallback Strategy
If filters return fewer than 3 results:
1. Relax the rating threshold by `–0.5`
2. If still insufficient, relax budget by one tier
3. Always surface at least 3 candidates for Groq to reason over

---

### 3.5 Prompt Builder

**Responsibility**: Construct the Groq prompt from candidate data and user intent.

#### Prompt Structure

```
[SYSTEM PROMPT]
You are a knowledgeable restaurant recommendation assistant.
Given a list of restaurants and a user's preferences, your job is to:
1. Rank the restaurants from most to least suitable.
2. Provide a brief, personalized explanation for each.
3. Be honest — if a restaurant only partially fits, say so.
Output format: JSON array of ranked recommendations.

[USER PROMPT]
User Preferences:
- Location: {location}
- Budget: {budget} (up to ₹{budget_ceiling} for two)
- Cuisine: {cuisine}
- Minimum Rating: {min_rating}
- Additional Notes: {extra_preferences}

Available Restaurants:
{formatted_candidate_list}

Please rank and explain these options.
```

#### Token Budget Management
- Estimate tokens per candidate (~80–120 tokens)
- If candidate list exceeds 80% of the model's context window, trim to the top-scoring candidates by rating before prompting

---

### 3.6 Recommendation Engine (Groq)

**Responsibility**: Reason over candidate restaurants and produce ranked, explained recommendations via the **Groq API**.

#### Groq's Role
Groq is **not** a data source — it never invents restaurants. It acts as a **reasoning and ranking layer** over data already filtered and verified by the pipeline. Groq's ultra-low-latency inference makes it ideal for delivering near-instant recommendations.

#### Groq Tasks
| Task | Description |
|---|---|
| **Ranking** | Order candidates by how well they match the full user intent, including soft preferences |
| **Explanation** | Write a 1–2 sentence human-readable justification per restaurant |
| **Summary** (optional) | A brief overall summary of the recommendation set |

#### Groq Interface Contract

**Input** (via prompt):
```json
{
  "user_preferences": { ... },
  "candidates": [ { "name": "...", "cuisine": "...", "rating": 4.2, "cost": 500 }, ... ]
}
```

**Expected Output**:
```json
[
  {
    "rank": 1,
    "name": "Spice Garden",
    "cuisine": "North Indian",
    "rating": 4.5,
    "cost": 450,
    "explanation": "Spice Garden is an excellent fit — it's highly rated, within your budget, and well-known for family-friendly seating."
  },
  ...
]
```

---

### 3.7 Response Formatter

**Responsibility**: Parse and validate Groq's raw output into a display-ready structure.

- Parse JSON from Groq's response (with error handling for malformed output)
- Validate required fields (`name`, `rank`, `explanation`) are present
- Fall back to a template explanation if Groq skips one
- Return a typed list of `Recommendation` objects

---

### 3.8 Output Display

**Responsibility**: Present the final recommendations to the user in a clear, readable format.

Each recommendation card displays:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🥇  #1 — Spice Garden
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🍜  Cuisine   : North Indian
⭐  Rating    : 4.5 / 5.0
💰  Cost      : ₹450 for two
🤖  Why this? : Spice Garden is an excellent fit — it's highly
                rated, within your budget, and well-known for
                family-friendly seating.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 4. Data Flow Summary

```
User Input
  → Preference Validator          [validates & normalizes inputs]
  → Data Ingestion Layer          [loads & preprocesses Zomato dataset]
  → Filtering Engine              [hard-constraint filtering → shortlist]
  → Prompt Builder                [formats shortlist + preferences into Groq prompt]
  → Recommendation Engine (Groq)  [ranks candidates, generates explanations]
  → Response Formatter            [parses & validates Groq output]
  → Output Display                [renders results to user]
```

---

## 5. Key Architectural Principles

| Principle | How It's Applied |
|---|---|
| **Separation of concerns** | Each layer has one job; filters never touch Groq, Groq never touches raw data |
| **Groq as reasoner, not retriever** | Groq only sees pre-filtered, real data — it cannot hallucinate restaurant facts |
| **Graceful degradation** | Fallback logic in filtering and response parsing ensures the system always returns something useful |
| **Explainability by design** | Every recommendation includes a human-readable explanation — not just a score |
| **Decoupled UI** | The pipeline accepts a `UserPreferences` object; any interface (CLI, API, web) can feed into it |

---

## 6. Technology Stack (Planned)

| Layer | Technology |
|---|---|
| Dataset Loading | `datasets` (Hugging Face) |
| Data Processing | `pandas` |
| LLM Integration | [Groq API](https://console.groq.com/) (`groq` Python SDK) |
| Backend / API | Python (FastAPI or CLI script) |
| Output | CLI (rich/tabulate) or Web UI |

---

## 7. Future Extensibility

- **Vector Search**: Embed restaurant descriptions and use semantic similarity search (e.g., FAISS, Chroma) as an alternative to keyword-based filtering — useful for vague queries like "something cozy"
- **User History**: Persist user sessions to personalize future recommendations
- **Multi-turn Conversation**: Support follow-up queries like "show me cheaper options" or "only vegetarian ones"
- **Feedback Loop**: Collect thumbs up/down to fine-tune ranking over time
