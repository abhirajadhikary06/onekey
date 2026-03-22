import typer
from rich import print as rprint
from ..common import get_client, console

llm_app = typer.Typer(help="LLM operations")

@llm_app.command("chat")
def llm_chat(
    provider: str = typer.Argument(..., help="LLM Provider (e.g. openai, groq)"),
    model: str = typer.Option(..., prompt="Model name", help="Model to use"),
    message: str = typer.Option(..., prompt="Your message", help="User message/prompt")
):
    """Call a Chat LLM via Onekey SDK."""
    client = get_client()
    with console.status(f"[cyan]Calling {provider} ({model})...[/cyan]"):
        try:
            resp = client.llm.chat(provider, model, [{"role": "user", "content": message}])
            rprint(resp)
        except Exception as e:
            console.print(f"[red]{str(e)}[/red]")

@llm_app.command("embed")
def llm_embed(
    provider: str = typer.Argument(..., help="LLM Provider"),
    model: str = typer.Option(..., prompt="Model name"),
    text: str = typer.Option(..., prompt="Text to embed")
):
    """Generate embeddings for text."""
    client = get_client()
    try:
        resp = client.llm.embed(provider, model, text)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")
