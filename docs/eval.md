# Evaluation Criteria: AI-Powered Food Place Recommender

## Overview

This document defines the evaluation criteria for each implementation phase. For each phase, criteria are broken into three tiers:

- ✅ **Must Pass** — Non-negotiable. Phase is not done until all of these pass.
- ⚠️ **Should Pass** — Important quality checks. Failures must be documented with a remediation plan.
- 💡 **Nice to Have** — Optional improvements that signal polish and production-readiness.

---

## Phase 1 — Project Setup & Environment

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E1.1 | Project installs cleanly with `pip install -r requirements.txt` in a fresh virtualenv | Run install in a new venv; check exit code = 0 |
| E1.2 | `python main.py` runs without errors | Execute and check for no exceptions |
| E1.3 | `.env.example` exists and documents all required environment variables | Manually inspect file |
| E1.4 | `src/` directory structure matches the architecture spec | Compare directory tree to spec in implementation plan |
| E1.5 | `.gitignore` excludes `.env`, `__pycache__`, `*.pyc`, and virtualenv directories | Review `.gitignore` contents |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E1.6 | All dependency versions are pinned in `requirements.txt` | Check that no `>=` or `~=` unpinned ranges are used for core deps |
| E1.7 | `README.md` has a "Getting Started" section | Manually read README |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E1.8 | `Makefile` or `setup.sh` automates venv creation and install | Attempt to run setup script from scratch |
| E1.9 | Pre-commit hooks configured (e.g., `flake8`, `black`) | Run `git commit` and verify hooks trigger |

---

## Phase 2 — Data Ingestion & Preprocessing

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E2.1 | `load_and_preprocess()` returns a non-empty Pandas DataFrame | Assert `len(df) > 0` |
| E2.2 | Output DataFrame contains exactly the required columns: `name`, `location`, `cuisines`, `cost`, `rating` | Assert `set(required_cols).issubset(df.columns)` |
| E2.3 | All `cost` values in output are integers or `None` | Assert `df['cost'].dropna().apply(lambda x: isinstance(x, int)).all()` |
| E2.4 | All `rating` values in output are floats or `None` | Assert `df['rating'].dropna().apply(lambda x: isinstance(x, float)).all()` |
| E2.5 | `"NEW"`, `"-"`, and empty strings in rating column are converted to `None` | Unit test with mock data containing these values |
| E2.6 | `location` values are lowercased and stripped of whitespace | Assert no uppercase in `df['location']` |
| E2.7 | Duplicate rows (same `name` + `location`) are removed | Count duplicates before and after; assert 0 after |
| E2.8 | Unit tests for all preprocessing functions pass | Run `pytest tests/test_preprocessing.py` |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E2.9 | Preprocessing runs in under 30 seconds on standard hardware | Time `load_and_preprocess()` call |
| E2.10 | A count of dropped rows is logged at `INFO` level | Check logs after preprocessing |
| E2.11 | Multi-cuisine strings (e.g., `"North Indian, Chinese"`) are correctly split into a list | Unit test with known multi-cuisine row |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E2.12 | Preprocessed DataFrame is cached locally (e.g., as `.parquet`) to avoid re-downloading | Check if cache file is created on second run |
| E2.13 | Data summary (row count, city count, cuisine count) is logged on startup | Inspect log output |

---

## Phase 3 — User Input & Preference Validation

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E3.1 | `validate_preferences()` returns a correctly populated `UserPreferences` object for all valid inputs | Unit test with valid inputs across all fields |
| E3.2 | Budget `"low"` → `budget_ceiling = 300`, `"medium"` → `700`, `"high"` → `9999` | Unit test all three mappings |
| E3.3 | Invalid budget value (e.g., `"expensive"`) raises `ValueError` with a descriptive message | Unit test with bad budget; assert `ValueError` raised |
| E3.4 | `min_rating` above 5.0 is clamped to 5.0 | Unit test with `min_rating=6.0`; assert `preferences.min_rating == 5.0` |
| E3.5 | `min_rating` below 0.0 is clamped to 0.0 | Unit test with `min_rating=-1.0`; assert `preferences.min_rating == 0.0` |
| E3.6 | Non-numeric `min_rating` input raises a clear error | Unit test with `"four"`; assert error raised |
| E3.7 | `location` and `cuisine` are normalized (lowercased, stripped) | Unit test with `"  DELHI  "` → assert `preferences.location == "delhi"` |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E3.8 | Empty `extra_preferences` is handled without error | Unit test with empty string; assert no exception |
| E3.9 | `extra_preferences` longer than 300 characters is truncated | Unit test with 500-char string; assert `len(preferences.extra_preferences) <= 300` |
| E3.10 | CLI input loop re-prompts user on invalid input instead of crashing | Manual test: enter bad value; verify re-prompt appears |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E3.11 | Available cities are listed as autocomplete hints during CLI input | Manual test of CLI interface |
| E3.12 | Available cuisines in the dataset are listed as hints | Manual test of CLI interface |

---

## Phase 4 — Filtering Engine

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E4.1 | `filter_restaurants()` returns a list of dicts, each with `name`, `location`, `cuisines`, `cost`, `rating` | Assert output schema on known input |
| E4.2 | All returned restaurants are in the correct city | Assert `all(r['location'] == preferences.location for r in results)` |
| E4.3 | All returned restaurants have `cost <= budget_ceiling` | Assert on each result |
| E4.4 | All returned restaurants have `rating >= min_rating` (or `None` excluded) | Assert on each result |
| E4.5 | Fallback relaxation triggers when fewer than 3 results are returned | Unit test with highly restrictive preferences; assert at least 3 results returned |
| E4.6 | Output is capped at N=20 results | Assert `len(results) <= 20` |
| E4.7 | Results are sorted by rating descending | Assert `results[0]['rating'] >= results[-1]['rating']` |
| E4.8 | Unit tests for all filter functions pass | Run `pytest tests/test_filters.py` |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E4.9 | Fuzzy cuisine matching correctly handles common misspellings | Unit test: `"chineese"` → matches `"chinese"` |
| E4.10 | Filtering a 10,000+ row DataFrame completes in under 2 seconds | Time `filter_restaurants()` with full dataset |
| E4.11 | Each fallback relaxation step is logged at `INFO` level | Check logs with restrictive preferences |
| E4.12 | When no results remain after all relaxations, a `NoResultsError` is raised | Unit test with impossible preferences; assert `NoResultsError` |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E4.13 | Filtering stats (rows before/after each filter step) logged at `DEBUG` level | Inspect debug logs |
| E4.14 | Filter pipeline is configurable (N, fallback thresholds) via config file | Check for config file support |

---

## Phase 5 — Groq Integration & Prompt Builder

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E5.1 | Groq API call succeeds with a valid API key | Run with real key; assert non-null response |
| E5.2 | Missing `GROQ_API_KEY` raises `ConfigError` at startup, not mid-run | Remove key from `.env`; run; assert `ConfigError` raised before filter/prompt steps |
| E5.3 | Built prompt contains all user preference fields | Unit test: check all fields present in prompt string |
| E5.4 | Built prompt contains all candidate restaurant entries | Unit test: check each candidate name appears in prompt |
| E5.5 | Prompt respects token budget: candidate list is trimmed if over 80% of 8192 tokens | Unit test with large candidate list; assert prompt token count ≤ 6553 |
| E5.6 | Groq returns a non-empty response string | Assert `len(response) > 0` |
| E5.7 | Groq API rate limit is retried with exponential backoff (up to 3 retries) | Mock a `429` response 2 times; assert 3rd call succeeds |
| E5.8 | Groq API timeout is handled gracefully | Mock a timeout; assert user-friendly error message shown |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E5.9 | Prompt template unit tests cover all variable substitutions | Run `pytest tests/test_prompt.py` |
| E5.10 | Groq call latency is under 10 seconds for a typical prompt | Time a real API call; log latency |
| E5.11 | Special characters in restaurant names are safely escaped before prompt injection | Unit test with restaurant names containing `"` and `\n` |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E5.12 | Prompt and response are logged at `DEBUG` level for inspection | Enable debug logging; verify prompt logged |
| E5.13 | Groq model is configurable via environment variable | Set `GROQ_MODEL=openai/gpt-oss-120b` in `.env`; verify it is used |

---

## Phase 6 — Response Formatter & Output Display

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E6.1 | `parse_groq_response()` correctly parses a valid JSON response into a list of `Recommendation` objects | Unit test with known valid JSON |
| E6.2 | JSON wrapped in markdown code fences is correctly extracted and parsed | Unit test with ` ```json ... ``` ` wrapped response |
| E6.3 | Recommendations with missing `explanation` field use the fallback template text | Unit test with JSON missing `explanation`; assert fallback used |
| E6.4 | Recommendations with missing `name` or `rank` are skipped and a warning is logged | Unit test; assert malformed items excluded from output |
| E6.5 | Output `Recommendation` objects are sorted by `rank` ascending | Assert `results[0].rank == 1` |
| E6.6 | `cost` and `rating` values in display are sourced from the dataset (re-joined), not from Groq output | Assert dataset value used when Groq returns a different value |
| E6.7 | `display_recommendations()` renders all required fields per card: name, cuisine, rating, cost, explanation | Visual inspection + unit test on output string |
| E6.8 | Groq-hallucinated restaurant names (not in candidate list) are filtered out before display | Unit test: Groq returns extra name not in candidates; assert it is excluded |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E6.9 | A completely unparseable Groq response triggers `ResponseParseError` with a clear user message | Unit test with garbage input; assert `ResponseParseError` raised |
| E6.10 | Display works in terminals without `rich` support (plain text fallback) | Test in a basic terminal; confirm readable output |
| E6.11 | When results were produced under relaxed filter conditions, a notice is shown to the user | Run with restrictive preferences; assert relaxation notice appears in output |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E6.12 | Output is exportable to a JSON file via `--output results.json` CLI flag | Run with flag; verify file created |
| E6.13 | Recommendation cards are visually distinguished (colored borders, bold titles) in `rich` output | Manual visual inspection |

---

## Phase 7 — End-to-End Testing & Hardening

### ✅ Must Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E7.1 | Full end-to-end test passes: known preferences → verify top recommendation is in the correct city and cuisine | Run `pytest tests/test_e2e.py` |
| E7.2 | Pipeline with a city that has sparse data (< 5 restaurants) returns at least 1 result with fallback | Run with a sparse city |
| E7.3 | Pipeline with a completely unknown city returns a friendly "no results" message without crashing | Run with `location="xyz_unknown"` |
| E7.4 | Unhandled exceptions at the top level are caught and displayed as user-friendly messages | Force an unexpected error; assert traceback is NOT shown to user |
| E7.5 | All unit tests across all phases pass | Run `pytest tests/` — 0 failures |
| E7.6 | All public functions have docstrings | Run `pydocstyle src/` or manual review |

### ⚠️ Should Pass
| ID | Criterion | How to Verify |
|---|---|---|
| E7.7 | `pylint` / `flake8` report 0 errors (warnings acceptable) | Run linter; check output |
| E7.8 | Full pipeline runtime (excluding dataset download) is under 20 seconds | Time `main.py` run with cached dataset |
| E7.9 | README accurately documents setup, env variables, and usage | Follow README from scratch; verify it works |

### 💡 Nice to Have
| ID | Criterion | How to Verify |
|---|---|---|
| E7.10 | Code coverage is ≥ 80% | Run `pytest --cov=src` |
| E7.11 | CI/CD pipeline (GitHub Actions) runs tests on every push | Push a commit; check Actions tab |

---

## Phase 8 — Future Enhancements (Optional)

> These criteria only apply if Phase 8 features are implemented.

| ID | Feature | Evaluation Criterion |
|---|---|---|
| E8.1 | Vector Search | Semantic query `"cozy place for a date"` returns contextually relevant results without explicit cuisine/location match |
| E8.2 | Web UI | UI renders in a modern browser; all CLI features are accessible via the web interface |
| E8.3 | Multi-turn Conversation | Follow-up query `"show me cheaper options"` correctly narrows previous results without restarting the pipeline |
| E8.4 | User History | Second run with the same user ID reflects previous preferences as defaults |
| E8.5 | Feedback Loop | After 10 thumbs-up/down interactions, ranking order changes measurably for the same input |
| E8.6 | Caching | Identical preferences on a second call return results without a new Groq API call (cache hit logged) |

---

## Summary Scorecard Template

Use this after completing each phase:

| Phase | Must Pass | Should Pass | Nice to Have | Status |
|---|---|---|---|---|
| 1 — Setup | `_/5` | `_/2` | `_/2` | 🔴 / 🟡 / 🟢 |
| 2 — Data Ingestion | `_/8` | `_/3` | `_/2` | 🔴 / 🟡 / 🟢 |
| 3 — User Input | `_/7` | `_/3` | `_/2` | 🔴 / 🟡 / 🟢 |
| 4 — Filtering | `_/8` | `_/4` | `_/2` | 🔴 / 🟡 / 🟢 |
| 5 — Groq Integration | `_/8` | `_/3` | `_/2` | 🔴 / 🟡 / 🟢 |
| 6 — Output Display | `_/8` | `_/3` | `_/2` | 🔴 / 🟡 / 🟢 |
| 7 — Testing | `_/6` | `_/3` | `_/2` | 🔴 / 🟡 / 🟢 |
| 8 — Enhancements | `N/A` | `N/A` | `_/6` | Optional |

**Legend**: 🔴 Incomplete &nbsp;&nbsp; 🟡 Partially done &nbsp;&nbsp; 🟢 Complete
