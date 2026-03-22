import typer
from rich import print as rprint
from ..common import get_client, console

db_app = typer.Typer(help="Database operations")

@db_app.command("query")
def db_query(
    provider: str = typer.Argument(..., help="DB Provider (e.g. postgres, snowflake)"),
    sql: str = typer.Option(..., prompt="SQL Query")
):
    """Execute a SQL query."""
    client = get_client()
    try:
        resp = client.database.query(provider, query=sql)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")

@db_app.command("list-tables")
def db_list_tables(provider: str = typer.Argument(...)):
    """List tables in the database."""
    client = get_client()
    try:
        resp = client.database.list_tables(provider)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")
