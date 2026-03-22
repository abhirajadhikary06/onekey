import os
import json
from onekey_sdk import OnekeyClient
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

console = Console()

def test_sdk():
    # 1. Initialize Client
    # We check for multiple common environment variable names
    api_key = os.getenv("ONEKEY_API_KEY") or os.getenv("ONEKEY_PLATFORM_API_KEY")
    
    if not api_key:
        console.print("[red]Error: API Key not found in environment or .env file.[/red]")
        console.print("Please ensure [bold]ONEKEY_API_KEY[/bold] is set.")
        console.print("You can run: [bold]export ONEKEY_API_KEY=your_key_here[/bold]")
        console.print("Or add [bold]ONEKEY_API_KEY=your_key_here[/bold] to your .env file.")
        return

    base_url = os.getenv("ONEKEY_BASE_URL", "http://127.0.0.1:8000")
    client = OnekeyClient(base_url=base_url, platform_api_key=api_key)
    console.print(Panel(f"Testing Onekey SDK\nBase URL: [cyan]{client.base_url}[/cyan]\nAPI Key: [green]{api_key[:5]}...{api_key[-5:]}[/green]", title="SDK Initialization"))

    # 2. Test LLM Category (GROQ focus)
    console.print("\n[bold cyan]1. Testing LLM Category (Groq)...[/bold cyan]")
    try:
        # User specifically asked for groq
        chat_resp = client.llm.chat("groq", "llama-3.3-70b-versatile", [{"role": "user", "content": "How's the weather in Groq?"}])
        console.print(f"Groq Chat Response: [green]Success[/green]")
        rprint(chat_resp)
    except Exception as e:
        console.print(f"Groq LLM Error: [red]{str(e)}[/red]")

    # 3. Test OpenRouter
    console.print("\n[bold cyan]2. Testing LLM Category (OpenRouter)...[/bold cyan]")
    try:
        chat_resp = client.llm.chat("openrouter", "google/gemini-2.0-flash-001", [{"role": "user", "content": "Tell me a joke about OpenRouter."}])
        console.print(f"OpenRouter Chat Response: [green]Success[/green]")
        rprint(chat_resp)
    except Exception as e:
        console.print(f"OpenRouter LLM Error: [red]{str(e)}[/red]")

    # 4. Test Database Category
    console.print("\n[bold cyan]2. Testing Database Category...[/bold cyan]")
    try:
        tables = client.database.list_tables("postgres")
        console.print(f"List Tables: [green]{tables}[/green]")
        
        # query_resp = client.database.query("postgres", "SELECT * FROM users LIMIT 1")
        # console.print(f"Query Response: [green]Success[/green]")
    except Exception as e:
        console.print(f"Database Error: [red]{str(e)}[/red]")

    # 4. Test Vector DB Category
    console.print("\n[bold cyan]3. Testing Vector DB Category...[/bold cyan]")
    try:
        collections = client.vector_db.list_collections("pinecone")
        console.print(f"Collections: [green]{collections}[/green]")
        
        # query_resp = client.vector_db.query("pinecone", collection="test", query_vector=[0.1]*1536)
        # console.print(f"Vector Query: [green]Success[/green]")
    except Exception as e:
        console.print(f"Vector DB Error: [red]{str(e)}[/red]")

    # 5. Test DevOps Category
    console.print("\n[bold cyan]4. Testing DevOps Category...[/bold cyan]")
    try:
        repos = client.devops.list_repos("github")
        console.print(f"Repos Found: [green]{len(repos) if isinstance(repos, list) else 'N/A'}[/green]")
    except Exception as e:
        console.print(f"DevOps Error: [red]{str(e)}[/red]")

    # 6. Test Data Engineering Category
    console.print("\n[bold cyan]5. Testing Data Engineering Category...[/bold cyan]")
    try:
        jobs = client.data_engineering.list_jobs("fivetran")
        console.print(f"Jobs Info: [green]{jobs}[/green]")
    except Exception as e:
        console.print(f"Data Engineering Error: [red]{str(e)}[/red]")

    # 7. Test External APIs Category
    console.print("\n[bold cyan]6. Testing External APIs Category...[/bold cyan]")
    try:
        # These usually require specific provider setup in Onekey
        # email_resp = client.apis.send_email("resend", to="test@example.com", subject="Test", body="Hi")
        # console.print(f"Email Sent: [green]Success[/green]")
        console.print("[yellow]Skipping live API tests (SMS/Email) to avoid costs/undelivered messages.[/yellow]")
    except Exception as e:
        console.print(f"APIs Error: [red]{str(e)}[/red]")

    console.print("\n[bold green]SDK Testing Complete![/bold green]")

if __name__ == "__main__":
    test_sdk()
