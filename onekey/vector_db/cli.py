import json
import typer
from rich import print as rprint
from ..common import get_client, console

vdb_app = typer.Typer(help="Vector Database operations")

@vdb_app.command("query")
def vdb_query(
    provider: str = typer.Argument(..., help="Vector DB Provider (e.g. pinecone, qdrant)"),
    collection: str = typer.Option(..., prompt="Collection/Index Name"),
    vector_json: str = typer.Option(..., prompt="Query Vector (JSON list)")
):
    """Query a Vector Database."""
    client = get_client()
    try:
        vector = json.loads(vector_json)
        resp = client.vector_db.query(provider, collection=collection, query_vector=vector)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")

@vdb_app.command("list-collections")
def vdb_list_collections(provider: str = typer.Argument(..., help="Provider")):
    """List all collections in a vector DB."""
    client = get_client()
    try:
        resp = client.vector_db.list_collections(provider)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")
