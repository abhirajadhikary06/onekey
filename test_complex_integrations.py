import os
from onekey import OnekeyClient
from rich import print as rprint
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()

console = Console()

def test_complex():
    client = OnekeyClient()
    console.print(f"Using Platform Key: [yellow]{client.platform_api_key[:10]}...[/yellow]\n")

    # 1. Test Vercel (DevOps)
    console.print("[bold cyan]1. Testing Vercel (DevOps)[/bold cyan]")
    try:
        projects = client.devops.list_projects("vercel")
        if isinstance(projects, dict) and "projects" in projects:
            console.print(f"[green]Successfully fetched {len(projects['projects'])} Vercel projects![/green]")
            for p in projects["projects"][:3]:
                console.print(f"- {p.get('name')} ({p.get('id')})")
        else:
            rprint(projects)
    except Exception as e:
        console.print(f"[red]Vercel Error: {e}[/red]")

    # 2. Test Render (DevOps)
    console.print("\n[bold cyan]2. Testing Render (DevOps)[/bold cyan]")
    try:
        services = client.devops.list_services("render")
        if isinstance(services, list):
            console.print(f"[green]Successfully fetched {len(services)} Render services![/green]")
            for s in services[:3]:
                service = s.get("service", {})
                console.print(f"- {service.get('name')} ({service.get('type')})")
        else:
            rprint(services)
    except Exception as e:
        console.print(f"[red]Render Error: {e}[/red]")

    # 3. Test NeonDB (Database)
    console.print("\n[bold cyan]3. Testing NeonDB (Database)[/bold cyan]")
    try:
        projects = client.database.list_projects("neondb")
        if isinstance(projects, dict) and "projects" in projects:
            console.print(f"[green]Successfully fetched {len(projects['projects'])} NeonDB projects![/green]")
            for p in projects["projects"][:3]:
                console.print(f"- {p.get('name')} ({p.get('id')})")
        else:
            rprint(projects)
    except Exception as e:
        console.print(f"[red]NeonDB Error: {e}[/red]")

if __name__ == "__main__":
    test_complex()
