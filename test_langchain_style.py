import os
from onekey import ChatOnekey, HumanMessage, SystemMessage
from rich import print as rprint
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()

console = Console()

def test_langchain_style():
    console.print("[bold cyan]Testing LangChain-style SDK Interface[/bold cyan]")
    
    # 1. Initialize ChatOnekey for Groq
    console.print("\n[bold]1. Testing Groq with .invoke()[/bold]")
    chat_groq = ChatOnekey(provider="groq", model="llama-3.3-70b-versatile")
    
    try:
        # Test with simple string (automatic conversion to HumanMessage)
        resp = chat_groq.invoke("Say hello in one word.")
        console.print(f"Response (String input): [green]{resp.content}[/green]")
        
        # Test with list of messages
        resp2 = chat_groq.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What is the capital of France?")
        ])
        console.print(f"Response (Message list): [green]{resp2.content}[/green]")
        
    except Exception as e:
        console.print(f"[red]Groq Error: {e}[/red]")

    # 2. Initialize ChatOnekey for OpenRouter
    console.print("\n[bold]2. Testing OpenRouter with .invoke()[/bold]")
    chat_opr = ChatOnekey(provider="openrouter", model="google/gemini-2.0-flash-001")
    
    try:
        resp = chat_opr.invoke("Tell me a one-liner joke.")
        console.print(f"Response: [green]{resp.content}[/green]")
    except Exception as e:
        console.print(f"[red]OpenRouter Error: {e}[/red]")

if __name__ == "__main__":
    test_langchain_style()
