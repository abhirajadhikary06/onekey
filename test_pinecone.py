import os
from onekey import OnekeyClient
from rich import print as rprint
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()

console = Console()

def test_pinecone():
    console.print("[bold cyan]Testing Pinecone Integration (Vector DB Category)[/bold cyan]")
    
    client = OnekeyClient()
    console.print(f"Using Platform Key: [yellow]{client.platform_api_key[:10]}...[/yellow]")
    
    try:
        console.print("\n[bold]Fetching your Pinecone indexes...[/bold]")
        # This calls the Onekey proxy for vector_db/pinecone
        indexes = client.vector_db.list_indexes("pinecone")
        
        if isinstance(indexes, dict) or isinstance(indexes, list):
            console.print("[green]Successfully connected to Pinecone![/green]")
            rprint(indexes)
        else:
            console.print("[yellow]Response received but unexpected format:[/yellow]")
            rprint(indexes)
            
    except Exception as e:
        console.print(f"[red]Pinecone Error: {e}[/red]")
        console.print("\n[yellow]Tip: Make sure you've added your Pinecone API Key to Onekey:[/yellow]")
        console.print("onekey add-key --provider pinecone --name my-pinecone --key \"your_api_key_here\"")

if __name__ == "__main__":
    test_pinecone()
