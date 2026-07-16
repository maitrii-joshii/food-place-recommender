# Project Context: AI-Powered Food Place Recommender

## Overview

This project is an **AI-powered restaurant recommendation system** inspired by platforms like Zomato. It intelligently suggests restaurants to users by combining structured restaurant data with the reasoning capabilities of a Large Language Model (LLM). The goal is to deliver personalized, human-like recommendations rather than simple filtered lists.

---

## Problem Being Solved

Traditional restaurant discovery relies on static filters and aggregate ratings. Users still have to manually sift through results that may technically match their criteria but don't actually fit their context or intent (e.g., "I want a quiet Italian place for a date night under ₹500 per person").

This system bridges that gap by:
- Accepting **natural, multi-dimensional user preferences** (location, budget, cuisine, rating, and freeform preferences like "family-friendly" or "quick service")
- Using **real-world restaurant data** (Zomato dataset from Hugging Face)
- Leveraging an **LLM to reason, rank, and explain** why each restaurant is a good fit — producing results that feel genuinely helpful and conversational

---

## Dataset

- **Source**: [Zomato Restaurant Recommendation Dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face
- **Key Fields Used**:
  - Restaurant Name
  - Location / City
  - Cuisine Type
  - Estimated Cost (for two)
  - User Rating

---

## System Architecture

```
User Input
    │
    ▼
Preference Collection
(Location, Budget, Cuisine, Min Rating, Extra Preferences)
    │
    ▼
Data Ingestion & Filtering Layer
(Load Zomato dataset → filter by structured criteria)
    │
    ▼
LLM Integration Layer
(Build a structured prompt with filtered restaurant data)
    │
    ▼
Recommendation Engine (LLM)
(Rank restaurants, generate explanations)
    │
    ▼
Output Display
(Restaurant Name, Cuisine, Rating, Cost, AI Explanation)
```

---

## Core Components

### 1. Data Ingestion
- Load and preprocess the Zomato dataset from Hugging Face.
- Extract and normalize relevant fields (name, location, cuisine, cost, rating).

### 2. User Input Collection
Gather structured preferences from the user:
| Preference | Example Values |
|---|---|
| Location | Delhi, Bangalore, Mumbai |
| Budget | Low / Medium / High |
| Cuisine | Italian, Chinese, Indian |
| Minimum Rating | e.g., 4.0+ |
| Additional Preferences | family-friendly, quick service, outdoor seating |

### 3. Integration Layer
- Filter the dataset based on structured user inputs (location, cuisine, budget range, minimum rating).
- Construct a prompt that passes the filtered restaurant list to the LLM.
- The prompt is designed to guide the LLM to **reason and rank** — not just list.

### 4. Recommendation Engine
The LLM is responsible for:
- **Ranking** shortlisted restaurants based on how well they match the user's full intent
- **Explaining** each recommendation in a human-readable way
- Optionally **summarizing** the choices for a quick overview

### 5. Output Display
Final output is presented in a clean, user-friendly format:
- Restaurant Name
- Cuisine Type
- Rating
- Estimated Cost
- AI-generated explanation of why this place fits the user's needs

---

## Key Design Decisions

- **Hybrid approach**: Structured filtering handles hard constraints (location, budget) efficiently, while the LLM handles soft reasoning (fit, explanation, ranking nuance).
- **LLM as a reasoning layer, not a data source**: The LLM never fabricates restaurant data — it only reasons over pre-filtered, real data passed to it via the prompt.
- **Explainability**: Every recommendation comes with a natural language explanation, making results trustworthy and useful.

---

## Goals & Success Criteria

- [ ] Successfully ingest and preprocess the Zomato dataset
- [ ] Collect user preferences via a clean interface
- [ ] Filter restaurants accurately based on structured criteria
- [ ] Generate meaningful, context-aware LLM recommendations
- [ ] Display results in a clear, readable format with explanations
