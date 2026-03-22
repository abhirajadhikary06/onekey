import typer
from rich import print as rprint
from ..common import get_client, console

de_app = typer.Typer(help="Data Engineering operations")

@de_app.command("list-jobs")
def de_list_jobs(provider: str = typer.Argument(..., help="DE Provider (e.g. fivetran, airbyte)")):
    """List data engineering sync jobs."""
    client = get_client()
    try:
        resp = client.data_engineering.list_jobs(provider)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")

@de_app.command("trigger-sync")
def de_trigger_sync(
    provider: str = typer.Argument(...),
    job_id: str = typer.Option(..., prompt="Job ID to trigger")
):
    """Trigger a sync job."""
    client = get_client()
    try:
        resp = client.data_engineering.trigger_sync(provider, job_id=job_id)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")
