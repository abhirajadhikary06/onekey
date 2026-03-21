import json
import os
from pathlib import Path
from datetime import datetime

import requests
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

app = typer.Typer(help="Onekey unified API key CLI")
console = Console()

CONFIG_DIR = Path.home() / ".onekey"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"base_url": "http://localhost:8000"}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def get_headers() -> dict:
    config = get_config()
    token = config.get("access_token")
    if not token:
        console.print("[red]Not logged in. Please run `onekey login` first.[/red]")
        raise typer.Exit(1)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def sparkline(data: list[int]) -> str:
    # A simple sparkline generator
    if not data:
        return ""
    sparks = list("  ▂▃▄▅▆▇█")
    min_d, max_d = min(data), max(data)
    if min_d == max_d:
        return sparks[4] * len(data)
    return "".join(sparks[int((len(sparks) - 1) * (d - min_d) / (max_d - min_d))] for d in data)


@app.command()
def login(
    base_url: str = typer.Option("https://onekey-ciwz.onrender.com", prompt="Backend URL (e.g. http://localhost:8000 or https://onekey-ciwz.onrender.com)", help="Base URL of Onekey server"),
    username: str = typer.Option(..., prompt="Username", help="Your Onekey username"),
    password: str = typer.Option(..., prompt="Password", hide_input=True, help="Your Onekey password"),
):
    """Authenticate and save JWT locally."""
    # Strip trailing slash
    base_url = base_url.rstrip("/")
    try:
        # FastAPI OAuth2PasswordRequestForm expects Form data, not JSON
        r = requests.post(f"{base_url}/auth/login", data={"username": username, "password": password})
        r.raise_for_status()
        data = r.json()
        
        config = get_config()
        config["base_url"] = base_url
        config["access_token"] = data["access_token"]
        save_config(config)
        console.print("[green]Successfully logged in![/green]")
    except requests.HTTPError as e:
        console.print(f"[red]Login failed: {e.response.status_code}[/red]")
        try:
            console.print(e.response.json().get('detail', 'Unknown error'))
        except BaseException:
            pass


@app.command()
def add_key(
    name: str = typer.Option(..., prompt="Key Name (e.g. primary-gpt4)", help="A user-friendly name"),
    key: str = typer.Option(..., prompt="The raw API Key", hide_input=True, help="The API key value"),
    provider: str = typer.Option("", prompt="Provider (Leave empty to auto-detect)", help="API Provider (e.g., openai, groq)"),
):
    """Save a new original API key to the Onekey platform."""
    config = get_config()
    base_url = config.get("base_url")

    payload = {"name": name, "key": key}
    if provider:
        payload["provider"] = provider

    try:
        r = requests.post(f"{base_url}/keys/", json=payload, headers=get_headers())
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
    except requests.HTTPError as e:
        console.print(f"[red]Failed to add key: {e.response.status_code}[/red]")
        try:
            console.print(e.response.json().get('detail', ''))
        except BaseException:
            pass


@app.command()
def ls():
    """List your encrypted API keys."""
    config = get_config()
    base_url = config.get("base_url")
    try:
        r = requests.get(f"{base_url}/keys/", headers=get_headers())
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
    except requests.HTTPError as e:
        console.print("[red]Failed to list keys.[/red]")


@app.command()
def usage(key_id: int = typer.Option(None, help="The Database ID of the key to inspect (from 'onekey ls')")):
    """View detailed usage and charts for a specific key."""
    config = get_config()
    base_url = config.get("base_url")
    headers = get_headers()
    
    try:
        if not key_id:
            # Let's list all keys to choose
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
        
        # If the backend returned just a list of logs, adapt that.
        # But backend/usage.py says it returns {"key": {...}, "logs": [...]}
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
    except requests.HTTPError as e:
        console.print(f"[red]Failed to load usage: {e.response.status_code}[/red]")


@app.command()
def call(
    unified_endpoint: str = typer.Option(..., prompt="Unified Endpoint (e.g. /proxy/u/openai/primary)", help="Unified API Endpoint"),
    model: str = typer.Option(..., prompt="Model name (e.g. llama-3.3-70b-versatile or gpt-4o)", help="Model to use"),
    message: str = typer.Option(..., prompt="Your prompt/message", help="Your prompt/message")
):
    """Test call to check proxy and unified key setup using your Platform Key."""
    config = get_config()
    base_url = config.get("base_url")

    # In legacy onekey_cli, user pasted 'unified_api_key'. Here we can fetch the Platform API Key automatically.
    # To call /proxy/u/..., we use Bearer {platform_api_key}.
    # We can fetch the platform key from /keys/platform-key
    try:
        r_key = requests.get(f"{base_url}/keys/platform-key", headers=get_headers())
        r_key.raise_for_status()
        platform_api_key = r_key.json()["platform_api_key"]
    except Exception as e:
        console.print("[red]Could not fetch platform API key.[/red]")
        return

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}]
    }

    with console.status(f"[cyan]Calling {unified_endpoint} via {model}...[/cyan]"):
        try:
            r = requests.post(
                f"{base_url}{unified_endpoint}",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {platform_api_key}"
                }
            )
            r.raise_for_status()
            
            json_str = json.dumps(r.json(), indent=2)
            
            colored_json = Text()
            for line in json_str.splitlines():
                if ':' in line and not line.strip().startswith('}'):
                    key, value = line.split(":", 1)
                    colored_json.append(Text(key, style="cyan"))
                    colored_json.append(Text(":", style="white"))
                    colored_json.append(Text(value, style="green"))
                else:
                    colored_json.append(Text(line, style="white"))
                colored_json.append("\n")

            console.print(Panel(
                colored_json,
                title=f"Full API Response • {model}",
                subtitle=f"Prompt: {message[:80]}{'...' if len(message) > 80 else ''}",
                border_style="bright_green",
                expand=True,
                padding=(1, 2)
            ))
        except requests.HTTPError as e:
            console.print(f"[red]✗ API call failed: {e.response.status_code}[/red]")
            console.print(e.response.text)


@app.command()
def docs(provider: str = typer.Argument(None)):
    """Show documentation URLs."""
    DOCS = {
        "groq": "https://onekey-ciwz.onrender.com/static/docs/groq.html",
        "openrouter": "https://onekey-ciwz.onrender.com/static/docs/openrouter.html",
        "gemini": "https://onekey-ciwz.onrender.com/static/docs/gemini.html",
        "openai": "https://onekey-ciwz.onrender.com/static/docs/openai.html",
        "anthropic": "https://onekey-ciwz.onrender.com/static/docs/anthropic.html",
        "mistral": "https://onekey-ciwz.onrender.com/static/docs/mistral.html",
        "perplexity": "https://onekey-ciwz.onrender.com/static/docs/perplexity.html"
    }

    if provider:
        p = provider.lower()
        if p in DOCS:
            console.print(f"Docs for {p}: [cyan]{DOCS[p]}[/cyan]")
        else:
            console.print(f"[red]Unknown provider: {p}[/red]")
        return
    
    table = Table(show_header=False, box=None)
    table.add_column("Provider", style="bold white")
    table.add_column("URL", style="cyan")
    
    for k, v in DOCS.items():
        table.add_row(k.capitalize(), v)
        
    console.print(Panel(table, title="Documentation Links", border_style="yellow", expand=False))


if __name__ == "__main__":
    app()
