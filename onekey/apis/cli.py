import typer
from rich import print as rprint
from ..common import get_client, console

api_app = typer.Typer(help="External API operations")

@api_app.command("send-sms")
def api_send_sms(
    provider: str = typer.Argument(..., help="API Provider (e.g. twilio)"),
    to: str = typer.Option(..., prompt="To Number"),
    body: str = typer.Option(..., prompt="Message Body")
):
    """Send an SMS via Onekey SDK."""
    client = get_client()
    try:
        resp = client.apis.send_sms(provider, to=to, body=body)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")

@api_app.command("send-email")
def api_send_email(
    provider: str = typer.Argument(..., help="Provider (e.g. sendgrid, resend)"),
    to: str = typer.Option(..., prompt="To Email"),
    subject: str = typer.Option(..., prompt="Subject"),
    body: str = typer.Option(..., prompt="Email Body")
):
    """Send an email."""
    client = get_client()
    try:
        resp = client.apis.send_email(provider, to=to, subject=subject, body=body)
        rprint(resp)
    except Exception as e:
        console.print(f"[red]{str(e)}[/red]")
