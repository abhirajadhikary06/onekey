import json
import os
from pathlib import Path
from typing import Optional
import requests
from rich.console import Console
from .client import OnekeyClient

console = Console()
CONFIG_DIR = Path.home() / ".onekey"
CONFIG_FILE = CONFIG_DIR / "config.json"

def get_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"base_url": "https://onekey-ciwz.onrender.com"}
    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {"base_url": "https://onekey-ciwz.onrender.com"}

def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_base_url() -> str:
    config = get_config()
    return os.getenv("ONEKEY_BASE_URL") or config.get("base_url") or "https://onekey-ciwz.onrender.com"

def get_client() -> OnekeyClient:
    api_key = os.getenv("ONEKEY_API_KEY")
    base_url = get_base_url()
    
    if not api_key:
        api_key = config.get("platform_api_key")
        
    if not api_key:
        console.print("[yellow]ONEKEY_API_KEY not found in environment or config.[/yellow]")
        import typer
        api_key = typer.prompt("Please enter your Onekey Platform API Key", hide_input=True)
        config["platform_api_key"] = api_key
        config["base_url"] = base_url
        save_config(config)
            
    return OnekeyClient(base_url=base_url, platform_api_key=api_key)

def get_auth_headers() -> dict:
    config = get_config()
    token = config.get("access_token") or config.get("platform_api_key")
    if not token:
        console.print("[red]No API key or token found. Please set ONEKEY_API_KEY env var.[/red]")
        import typer
        raise typer.Exit(1)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

def sparkline(data: list[int]) -> str:
    if not data:
        return ""
    sparks = list("  ▂▃▄▅▆▇█")
    min_d, max_d = min(data), max(data)
    if min_d == max_d:
        return sparks[4] * len(data)
    return "".join(sparks[int((len(sparks) - 1) * (d - min_d) / (max_d - min_d))] for d in data)
