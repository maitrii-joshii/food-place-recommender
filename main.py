import sys
import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm

from src.data import load_and_preprocess

from src.filters import filter_restaurants, NoResultsError
from src.ui import collect_preferences, display_recommendations
from src.prompt import build_system_prompt, build_user_prompt, NoCandidatesError
from src.groq_client import GroqClient, GroqClientError
from src.formatter import parse_llm_response, FormatterError

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True, markup=True, show_time=False, show_path=False)
    ],
)

# Silence verbose third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)
logging.getLogger("datasets").setLevel(logging.WARNING)

logger = logging.getLogger("main")
console = Console()


def main():
    try:
        # Step 1: Initialize Groq Client early to catch missing API keys before doing heavy work
        try:
            llm_client = GroqClient()
        except GroqClientError as e:
            console.print(f"\n[bold red]Configuration Error:[/bold red] {e}")
            sys.exit(1)

        # Step 2: Load Data
        with console.status(
            "[bold cyan]Loading restaurant database (this may take a moment on first run)...[/bold cyan]",
            spinner="dots",
        ):
            df = load_and_preprocess()

        # Step 3: Extract unique cities and cuisines for CLI hints
        cities = df["location"].dropna().unique().tolist()
        # Flatten cuisines lists
        all_cuisines = set(c for sublist in df["cuisines"].dropna() for c in sublist)
        cuisines = list(all_cuisines)

        # Step 4: Collect Preferences
        while True:
            prefs = collect_preferences(known_cities=cities, known_cuisines=cuisines)

            try:
                with console.status(
                    "[bold cyan]Filtering and analyzing matches...[/bold cyan]",
                    spinner="bouncingBar",
                ):
                    candidates = filter_restaurants(df, prefs, max_results=20)
            except NoResultsError as e:
                console.print(f"\n[bold yellow]No Matches Found:[/bold yellow] {e}")
                if Confirm.ask("Would you like to try different preferences?"):
                    continue
                else:
                    console.print("[green]Goodbye![/green]")
                    sys.exit(0)

            break  # Exit retry loop if filtering succeeded

        # Step 6: Build Prompts
        system_prompt = build_system_prompt()
        try:
            user_prompt = build_user_prompt(prefs, candidates)
        except NoCandidatesError as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            sys.exit(1)

        # Step 7: Call Groq API
        with console.status(
            "[bold purple]Asking AI for personalized recommendations...[/bold purple]",
            spinner="earth",
        ):
            raw_response = llm_client.generate_recommendations(
                system_prompt, user_prompt
            )

        # Step 8: Parse Response
        try:
            parsed_data = parse_llm_response(raw_response)
        except FormatterError as e:
            logger.warning(
                f"Failed to cleanly format response: {e}. Falling back to raw output."
            )
            parsed_data = raw_response

        # Step 9: Display Output
        display_recommendations(parsed_data)

    except KeyboardInterrupt:
        console.print(
            "\n[bold yellow]Operation cancelled by user. Goodbye![/bold yellow]\n"
        )
        sys.exit(0)
    except Exception:
        logger.exception("An unexpected error occurred")
        console.print(
            "\n[bold red]Fatal Error:[/bold red] Something went wrong. Check logs for details.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
