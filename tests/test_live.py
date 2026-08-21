"""
Live integration tests using real Groq API and real HuggingFace dataset.
Run with: python -m tests.test_live
"""

import sys
import os
import logging

# Force UTF-8 output on Windows
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

from rich.console import Console
from rich.rule import Rule

console = Console(force_terminal=True, highlight=False)


def run_test(
    test_name: str,
    location: str,
    budget: str,
    cuisine: str,
    min_rating: str,
    extra: str,
):
    from src.data.ingestion import load_and_preprocess
    from src.filters.preferences import validate_preferences
    from src.filters.engine import filter_restaurants, NoResultsError
    from src.prompt.builder import build_system_prompt, build_user_prompt
    from src.groq_client.client import GroqClient
    from src.formatter.parser import parse_llm_response
    from src.ui.cli import display_recommendations

    console.print(Rule(f"[bold cyan]{test_name}[/bold cyan]"))
    console.print(
        f"[dim]Location:[/dim] {location}  [dim]Budget:[/dim] {budget}  "
        f"[dim]Cuisine:[/dim] {cuisine or 'Any'}  [dim]Min Rating:[/dim] {min_rating}"
    )

    # 1. Load data (cached after first run)
    with console.status("[bold cyan]Loading dataset...[/bold cyan]", spinner="dots"):
        df = load_and_preprocess()
    console.print(
        f"[green]OK[/green] Dataset loaded -- {len(df):,} restaurants across {df['location'].nunique()} cities"
    )

    # 2. Validate preferences
    prefs = validate_preferences(
        location=location,
        budget=budget,
        cuisine=cuisine,
        min_rating=min_rating,
        extra_preferences=extra,
    )

    # 3. Filter
    with console.status(
        "[bold cyan]Filtering candidates...[/bold cyan]", spinner="bouncingBar"
    ):
        try:
            candidates = filter_restaurants(df, prefs, max_results=20)
        except NoResultsError as e:
            console.print(f"[bold red]FAIL No Results:[/bold red] {e}")
            return False

    console.print(
        f"[green]OK[/green] {len(candidates)} candidates shortlisted after filtering"
    )

    # 4. Build prompts
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(prefs, candidates)

    # 5. Real Groq API call
    console.print(
        "[bold purple]>> Calling Groq API (openai/gpt-oss-120b)...[/bold purple]"
    )
    with console.status(
        "[bold purple]Waiting for AI response...[/bold purple]", spinner="earth"
    ):
        client = GroqClient()
        raw_response = client.generate_recommendations(system_prompt, user_prompt)

    console.print(f"[green]OK[/green] Got response ({len(raw_response)} chars)")

    # 6. Parse
    parsed = parse_llm_response(raw_response)
    if isinstance(parsed, str):
        console.print("[yellow]WARN: Fallback to raw string display[/yellow]")
    else:
        console.print(
            f"[green]OK[/green] Parsed {len(parsed)} recommendations cleanly from JSON"
        )

    # 7. Display
    display_recommendations(parsed)
    return True


if __name__ == "__main__":
    passed = 0

    # --- Test Case 1: North Indian in BTM (a popular Bangalore neighborhood) ---
    result1 = run_test(
        test_name="Test 1 - BTM / North Indian / Medium Budget",
        location="btm",
        budget="medium",
        cuisine="north indian",
        min_rating="4.0",
        extra="family-friendly",
    )
    if result1:
        passed += 1

    console.print()

    # --- Test Case 2: Chinese food in Indiranagar, high budget ---
    result2 = run_test(
        test_name="Test 2 - Indiranagar / Chinese / High Budget",
        location="indiranagar",
        budget="high",
        cuisine="chinese",
        min_rating="4.2",
        extra="good ambience",
    )
    if result2:
        passed += 1

    console.print()
    console.print(Rule())
    console.print(
        f"[bold]Live Tests Complete:[/bold] {passed}/2 passed"
        if passed == 2
        else f"[bold yellow]Live Tests:[/bold yellow] {passed}/2 passed"
    )
