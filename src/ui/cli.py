from typing import Optional, List, Union, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from src.filters.preferences import validate_preferences, UserPreferences

console = Console()


def collect_preferences(
    known_cities: Optional[List[str]] = None, known_cuisines: Optional[List[str]] = None
) -> UserPreferences:
    """
    Collects preferences interactively from the CLI and returns a validated UserPreferences object.
    Automatically handles re-prompting on invalid input.
    """
    console.print(
        "\n[bold green]🍽️ Welcome to the AI-Powered Food Place Recommender![/bold green]\n"
    )
    console.print(
        "Let's find you the perfect place to eat. Please tell me your preferences.\n"
    )

    while True:
        # 1. Location
        if known_cities:
            # Show a few popular cities as hints
            hints = ", ".join(known_cities[:5])
            loc_prompt = f"Which city? (e.g., {hints})"
        else:
            loc_prompt = "Which city?"

        location = Prompt.ask(f"[bold cyan]{loc_prompt}[/bold cyan]")

        # 2. Budget
        budget = Prompt.ask(
            "[bold cyan]What is your budget?[/bold cyan]",
            choices=["low", "medium", "high"],
            default="medium",
        )

        # 3. Cuisine
        if known_cuisines:
            c_hints = ", ".join(known_cuisines[:5])
            cuisine_prompt = f"Any specific cuisine? (e.g., {c_hints}, or leave blank)"
        else:
            cuisine_prompt = "Any specific cuisine? (Leave blank for any)"

        cuisine = Prompt.ask(f"[bold cyan]{cuisine_prompt}[/bold cyan]", default="")

        # 4. Minimum Rating
        min_rating = Prompt.ask(
            "[bold cyan]Minimum rating? (0.0 to 5.0)[/bold cyan]", default="4.0"
        )

        # 5. Extra Preferences
        extra_preferences = Prompt.ask(
            "[bold cyan]Any other preferences? (e.g., 'family-friendly', 'outdoor seating', or leave blank)[/bold cyan]",
            default="",
        )

        try:
            prefs = validate_preferences(
                location=location,
                budget=budget,
                cuisine=cuisine,
                min_rating=min_rating,
                extra_preferences=extra_preferences,
            )
            console.print(
                "\n[bold green]Preferences recorded successfully![/bold green]\n"
            )
            return prefs
        except ValueError as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            console.print("[yellow]Please try again.[/yellow]\n")


def display_recommendations(parsed_data: Union[List[Dict[str, Any]], str]):
    """
    Displays the final recommendations in a beautiful Rich table.
    If the data is a raw string (fallback), it displays it in a panel.
    """

    if isinstance(parsed_data, str):
        # Fallback raw string display
        console.print(
            Panel(parsed_data, title="Recommendations", border_style="yellow")
        )
        return

    if not parsed_data:
        console.print("[bold red]No valid recommendations to display.[/bold red]")
        return

    table = Table(
        title="🏆 Top Restaurant Recommendations 🏆",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Rank", justify="center", style="cyan", no_wrap=True)
    table.add_column("Restaurant Name", style="bold white")
    table.add_column("Why We Recommend It", style="green")

    # Sort just in case it wasn't returned sorted
    parsed_data = sorted(parsed_data, key=lambda x: int(x.get("rank", 999)))

    for item in parsed_data:
        rank = str(item.get("rank", "-"))
        name = item.get("name", "Unknown")
        explanation = item.get("explanation", "")

        # Color top rank gold
        if rank == "1":
            rank_str = f"[bold yellow]🥇 {rank}[/bold yellow]"
            name_str = f"[bold yellow]{name}[/bold yellow]"
        elif rank == "2":
            rank_str = f"[bold bright_black]🥈 {rank}[/bold bright_black]"
            name_str = name
        elif rank == "3":
            rank_str = f"[bold color(130)]🥉 {rank}[/bold color(130)]"
            name_str = name
        else:
            rank_str = rank
            name_str = name

        table.add_row(rank_str, name_str, explanation)

    console.print("\n")
    console.print(table)
    console.print("\n[bold green]Bon Appétit! 🍽️[/bold green]\n")
