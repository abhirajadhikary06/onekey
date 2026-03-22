import typer
from rich import print as rprint
from ..common import get_client, console

devops_app = typer.Typer(help="DevOps operations")

@devops_app.command("list-repos")
def devops_list_repos(provider: str = typer.Argument(..., help="DevOps Provider (e.g. github, vercel)")):
    """List repositories or projects."""
    client = get_client()
    try:
        resp = client.devops.list_repos(provider)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")

@devops_app.command("list-issues")
def devops_list_issues(
    provider: str = typer.Argument(..., help="Provider"),
    repo: str = typer.Option(..., prompt="Repo name (owner/repo)")
):
    """List issues for a repository."""
    client = get_client()
    try:
        resp = client.devops.list_issues(provider, repo=repo)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")
