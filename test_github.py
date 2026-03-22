import os
from onekey import OnekeyClient
from rich import print as rprint
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()

console = Console()

def test_github():
    console.print("[bold cyan]Testing GitHub Integration (DevOps Category)[/bold cyan]")
    
    client = OnekeyClient()
    console.print(f"Using Platform Key: [yellow]{client.platform_api_key[:10]}...[/yellow]")
    
    try:
        console.print("\n[bold]Fetching all your GitHub repositories...[/bold]")
        # This calls GET https://api.github.com/user/repos via the Onekey proxy
        repos = client.devops.list_repos("github")
        
        if isinstance(repos, list):
            console.print(f"[green]Successfully fetched {len(repos)} repositories![/green]")
            for repo in repos:
                console.print(f"- [bold]{repo.get('full_name')}[/bold] ({repo.get('stargazers_count')} stars)")
        else:
            rprint(repos)
            
    except Exception as e:
        console.print(f"[red]GitHub Error: {e}[/red]")
        console.print("\n[yellow]Tip: Make sure you've added your GitHub PAT to Onekey:[/yellow]")
        console.print("onekey add-key --provider github --name my-github --key \"your_pat_here\"")

if __name__ == "__main__":
    test_github()
