# utils/ui_helpers.py
import os
import contextlib
import builtins
from typing import Any

from rich.console import Console
from rich.panel import Panel

# Initialize console here so splash() and other helpers can safely use it.
console = Console()

def splash() -> None:
    """Display ASCII logo and subtitle."""
    logo = r"""
   ██████╗  █████╗ ██╗
  ██╔═══██╗██╔══██╗██║
  ██║   ██║███████║██║
  ██║   ██║██╔══██║██║
  ╚██████╔╝██║  ██║███████╗
   ╚═════╝ ╚═╝  ╚═╝╚══════╝
    """
    console.print(Panel.fit(logo, title="[bold cyan]Qai Orchestrator[/]", border_style="cyan"))
    console.print("[dim]✨ Chat-driven AI crews for code & ideas ✨[/]\n")


def say_user(msg: str) -> None:
    """Print a user message panel."""
    console.print(Panel.fit(msg, title="[bold blue]You[/]", border_style="blue"))


def say_assistant(msg: str) -> None:
    """Print an assistant message panel."""
    console.print(Panel.fit(msg, title="[bold red]Assistant[/]", border_style="red"))


def say_system(msg: str) -> None:
    """Print a system message panel."""
    console.print(Panel.fit(msg, title="[bold green]System[/]", border_style="green"))


def say_success(msg: str) -> None:
    """Print a success panel (green, with checkmark)."""
    console.print(Panel.fit(f"✅ {msg}", title="[bold green]Success[/]", border_style="green"))


def say_error(msg: str) -> None:
    """Print an error panel (red, with cross)."""
    console.print(Panel.fit(f"❌ {msg}", title="[bold red]Error[/]", border_style="red"))
