# AI-Powered Food Place Recommender

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://food-place-recommender.streamlit.app/)

An intelligent restaurant recommendation CLI tool powered by the **Groq LLM API** (llama3-8b-8192).
It loads real-world Zomato restaurant data from Hugging Face, filters it against your preferences,
and uses AI to rank and explain the best options — all in seconds, right in your terminal.

---

## Features

- **Smart Filtering** — Filters by city, cuisine, budget, and minimum rating
- **Graceful Relaxation** — Intelligently loosens constraints when results are sparse
- **AI-Powered Ranking** — Groq LLM explains *why* each restaurant suits your needs
- **Beautiful CLI** — Rich terminal UI with color-coded tables
- **Local Caching** — Dataset is cached to Parquet after first download for instant re-runs
- **Robust Error Handling** — Rate-limit retries, model fallbacks, and JSON parse recovery

---

## Quick Start

### Prerequisites
- Python 3.9+
- A [Groq API Key](https://console.groq.com) (free tier available)

### 1. Clone & Set Up

```bash
git clone https://github.com/maitrii-joshii/food-place-recommender.git
cd food-place-recommender
```

**Windows:**
```bash
setup.bat
```

**Manual (macOS/Linux):**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

### 2. Configure Environment

Copy the example and fill in your Groq API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=llama3-8b-8192
```

### 3. Run the App

```bash
python main.py
```

On the **first run**, the Zomato dataset (~10MB) is downloaded from Hugging Face and cached locally as `zomato_cache.parquet`. Subsequent runs start instantly.

---

## Usage Example

```
Welcome to the AI-Powered Food Place Recommender!

Which city? (e.g., delhi, mumbai, bangalore): delhi
What is your budget? [low/medium/high] (medium): medium
Any specific cuisine? (e.g., north indian, chinese, italian, or leave blank): north indian
Minimum rating? (0.0 to 5.0) (4.0): 4.2
Any other preferences? (e.g., 'family-friendly', 'outdoor seating'): family-friendly

┌─────────────────────────────────────────────────────────────┐
│             Top Restaurant Recommendations                  │
├──────┬──────────────────────┬────────────────────────────────┤
│ Rank │ Restaurant Name      │ Why We Recommend It            │
├──────┼──────────────────────┼────────────────────────────────┤
│ 1    │ Spice Garden         │ Highly rated North Indian...   │
│ 2    │ Delhi Darbar         │ Great family atmosphere...     │
│ 3    │ Punjabi Dhaba        │ Excellent value for money...   │
└──────┴──────────────────────┴────────────────────────────────┘

Bon Appétit!
```

---

## Project Architecture

```
food-place-recommender/
├── docs/                    # Architecture, context, implementation plan, edge cases
├── src/
│   ├── data/                # Hugging Face dataset loading, cleaning & caching
│   ├── filters/             # Preference validation & filtering engine
│   ├── prompt/              # Groq prompt builder with token budget management
│   ├── groq_client/         # Groq API wrapper with retries & fallbacks
│   ├── formatter/           # JSON parsing & schema validation of LLM output
│   └── ui/                  # Rich CLI: input collection & results display
├── tests/                   # Unit + integration tests (37 tests)
├── main.py                  # Entry point — orchestrates the full pipeline
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── setup.bat                # Windows one-click setup script
```

### Pipeline Flow

```
User Input (CLI)
    └─► Preference Validator
            └─► Dataset (Hugging Face / Cache)
                    └─► Filtering Engine (location → budget → cuisine → rating)
                            └─► Prompt Builder (token-safe prompt)
                                    └─► Groq LLM (llama3-8b-8192)
                                            └─► Response Parser (JSON + fallback)
                                                    └─► Rich CLI Display
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# By module
pytest tests/test_preprocessing.py -v
pytest tests/test_engine.py -v
pytest tests/test_groq_client.py -v
pytest tests/test_prompt.py -v
pytest tests/test_parser.py -v
pytest tests/test_integration.py -v
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama3-8b-8192` | Groq model to use |

**Budget Tiers:**

| Tier | Max Cost (for two) |
|---|---|
| `low` | ₹300 |
| `medium` | ₹700 |
| `high` | Unlimited |

---

## Edge Case Handling

| Scenario | Behavior |
|---|---|
| City not in dataset | Raises `NoResultsError` with a re-prompt |
| Cuisine not found (exact) | Falls back to fuzzy matching |
| Too few results | Cascading relaxation (cuisine → rating → budget) |
| Groq rate limit hit | Exponential backoff with up to 3 retries |
| Groq model unavailable | Automatic fallback to `openai/gpt-oss-120b` |
| Malformed LLM JSON | Regex extraction + schema validation + raw string fallback |
| `NEW` / `-` ratings | Treated as `None` (unrated), excluded from rating filters |

---

## Dependencies

| Package | Purpose |
|---|---|
| `datasets` | Hugging Face dataset loading |
| `pandas` | Data manipulation |
| `pyarrow` | Parquet caching |
| `groq` | Groq Python SDK |
| `python-dotenv` | `.env` file support |
| `rich` | Beautiful terminal UI |

---

## License

MIT License — feel free to use, fork, and extend.
