import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import requests
import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

from .common import get_config, save_config, get_client, get_auth_headers, sparkline, console, get_base_url
from .registry import IntegrationRegistry
from .llm.cli import llm_app
from .database.cli import db_app
from .vector_db.cli import vdb_app
from .devops.cli import devops_app
from .apis.cli import api_app
from .data_engineering.cli import de_app

app = typer.Typer(help="Onekey unified API key CLI")

@app.command()
def list_providers():
    """List all supported AI and cloud providers by category."""
    registry = IntegrationRegistry()
    
    table = Table(title="Supported Onekey Integrations", show_lines=True)
    table.add_column("Category", style="bold cyan")
    table.add_column("Providers", style="green")

    for cat in registry.all_categories():
        providers = ", ".join(registry.providers_for(cat))
        table.add_row(cat.upper().replace("_", " "), providers)
    
    console.print(table)

app.add_typer(llm_app, name="llm")
app.add_typer(vdb_app, name="vdb")
app.add_typer(devops_app, name="devops")
app.add_typer(api_app, name="api")
app.add_typer(db_app, name="db")
app.add_typer(de_app, name="de")


@app.command()
def add_key(
    name: str = typer.Option(..., prompt="Key Name (e.g. primary-gpt4)", help="A user-friendly name"),
    key: str = typer.Option(..., prompt="The raw API Key", hide_input=True, help="The API key value"),
    provider: str = typer.Option("", prompt="Provider (Leave empty to auto-detect)", help="API Provider (e.g., openai, groq)"),
):
    """Save a new original API key to the Onekey platform."""
    base_url = get_base_url()

    payload = {"name": name, "key": key}
    if provider:
        payload["provider"] = provider

    try:
        r = requests.post(f"{base_url}/keys/", json=payload, headers=get_auth_headers())
        r.raise_for_status()
        data = r.json()
        console.print(Panel(
            f"[bold green]Key added successfully![/bold green]\n"
            f"ID: {data['id']}\n"
            f"Provider: [cyan]{data['provider']}[/cyan]\n"
            f"Unified API Key: [bold yellow]{data['unified_api_key']}[/bold yellow]\n"
            f"Use URL: [cyan]{base_url}{data['unified_endpoint']}[/cyan]",
            title="Success",
            expand=False
        ))
    except Exception as e:
        console.print(f"[red]Failed to add key: {str(e)}[/red]")


@app.command()
def ls():
    """List your encrypted API keys."""
    base_url = get_base_url()
    try:
        r = requests.get(f"{base_url}/keys/", headers=get_auth_headers())
        r.raise_for_status()
        keys = r.json()
        
        if not keys:
            console.print("[yellow]No keys found.[/yellow]")
            return

        table = Table(title="Your Onekey Vault")
        table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Provider", style="green")
        table.add_column("Created", style="dim")
        table.add_column("Masked Key", style="red")

        for k in keys:
            created = datetime.fromisoformat(k["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            table.add_row(str(k["id"]), k["name"], k["provider"], created, k["api_key"])
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to list keys: {str(e)}[/red]")


@app.command()
def usage(key_id: Optional[int] = typer.Option(None, help="The Database ID of the key to inspect")):
    """View detailed usage and charts for a specific key."""
    base_url = get_base_url()
    headers = get_auth_headers()
    
    try:
        if not key_id:
            r = requests.get(f"{base_url}/keys/", headers=headers)
            r.raise_for_status()
            keys = r.json()
            if not keys:
                console.print("[yellow]No keys found.[/yellow]")
                return
            console.print("Available Keys:")
            for k in keys:
                console.print(f"[{k['id']}] {k['provider']} - {k['name']}")
            key_id = int(typer.prompt("Enter the Key ID to view usage"))

        r = requests.get(f"{base_url}/usage/{key_id}", headers=headers)
        r.raise_for_status()
        data = r.json()
        logs = data.get("logs", [])
        key_info = data.get("key", {})
        title = f"Usage for {key_info.get('name', 'Unknown')} (ID {key_id})"

        if not logs:
            console.print(Panel("[yellow]No usage recorded yet.[/yellow]", title=title, border_style="yellow", expand=False))
            return

        logs.sort(key=lambda x: x["created_at"])
        tokens = [log["total_tokens"] for log in logs]
        times = [datetime.fromisoformat(log["created_at"].replace("Z", "+00:00")) for log in logs]

        spark = sparkline(tokens)
        total = sum(tokens)
        max_single = max(tokens) if tokens else 0
        calls = len(logs)
        time_range = f"{times[0].strftime('%b %d %Y')} → {times[-1].strftime('%b %d %Y')}"

        stats_text = Text.assemble(
            ("Total tokens: ", "bold green"), (f"{total:,}", "bold white"),
            ("\nHighest call: ", "bold green"), (f"{max_single:,}", "bold white"),
            ("\nTotal calls:  ", "bold green"), (f"{calls}", "bold white"),
            ("\nTime span:    ", "bold green"), (time_range, "bold white")
        )

        console.print(Panel(
            f"[bold cyan]{title}[/bold cyan]\n\n{spark}\n\n{stats_text}",
            title="Usage Curve & Stats",
            border_style="bright_blue",
            expand=False,
            padding=(1, 2)
        ))
    except Exception as e:
        console.print(f"[red]Failed to load usage: {str(e)}[/red]")


if __name__ == "__main__":
    app()
