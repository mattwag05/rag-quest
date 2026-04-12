"""Startup checks and friendly welcome screen."""

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_welcome_screen() -> None:
    """Print the welcome screen with ASCII art and friendly message."""
    console.clear()
    
    # ASCII Art Title
    title_art = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║          ██████╗  █████╗  ██████╗       ██████╗ ██╗   ██║
    ║          ██╔══██╗██╔══██╗██╔════╝       ██╔═══██╗██║   ██║
    ║          ██████╔╝███████║██║  ███╗█████╗██║   ██║██║   ██║
    ║          ██╔══██╗██╔══██║██║   ██║╚════╝██║▄▄ ██║██║   ██║
    ║          ██║  ██║██║  ██║╚██████╔╝      ╚██████╔╝╚██████╔╝
    ║          ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝        ╚══▀▀═══╝ ╚═════╝
    ║                                                          ║
    ║            Your AI Dungeon Master Awaits                ║
    ║         AI-Powered D&D with Knowledge Graphs            ║
    ║                  Version 0.5.2                          ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    
    console.print(title_art, style="cyan")
    console.print(
        Text(
            "An adventure shaped by knowledge graphs awaits...",
            justify="center",
            style="yellow"
        )
    )
    console.print()


def check_ollama_health(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running and accessible.
    
    Returns True if Ollama is healthy, False otherwise.
    """
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def get_available_ollama_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Get list of available Ollama models.
    
    Returns empty list if Ollama is not running.
    """
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
    except Exception:
        pass
    return []


def print_ollama_setup_needed() -> None:
    """Print friendly setup instructions for Ollama."""
    console.print(
        Panel(
            """[bold cyan]It looks like Ollama isn't running yet![/bold cyan]

RAG-Quest needs Ollama to power your AI dungeon master. It's free and runs 
completely on your computer — no internet connection required, no API keys, 
and your world stays private.

[bold]To get started:[/bold]

1. [cyan]Download Ollama[/cyan]
   Visit https://ollama.com and download the version for your system
   
2. [cyan]Install & Launch[/cyan]
   Open Ollama (it runs quietly in the background)
   
3. [cyan]Pull the Recommended Model[/cyan]
   Open Terminal and run:
   [dim]ollama pull gemma4[/dim]
   
   This takes 10-15 minutes depending on internet speed.
   Gemma 4 E4B (4B parameters) is perfect for RAG-Quest.
   
4. [cyan]Come Back Here[/cyan]
   Once Ollama is running, start RAG-Quest again!

[bold]Need Help?[/bold]
Visit https://github.com/yourusername/rag-quest for docs and troubleshooting.

[yellow]Press Enter to exit, then set up Ollama.[/yellow]""",
            title="[bold]Setup Required[/bold]",
            border_style="yellow",
        )
    )
    console.input()


def print_ollama_model_missing() -> None:
    """Print friendly message when Ollama runs but gemma4 isn't available."""
    console.print(
        Panel(
            """[bold cyan]Ollama is Running![/bold cyan]

Great! But we need to pull the [cyan]Gemma 4[/cyan] model first.
It's fast, free, and perfect for RAG-Quest.

[bold]In Terminal, run:[/bold]

[dim]ollama pull gemma4[/dim]

This downloads the model (~4-9 GB depending on variant).
It takes 10-30 minutes depending on your internet speed.

[bold]Recommended variants:[/bold]
- [cyan]gemma4:e4b[/cyan] - 4 billion parameters (best balance)
- [cyan]gemma4:e2b[/cyan] - 2 billion parameters (faster, CPU-only)
- [cyan]gemma4:latest[/cyan] - Latest version

[yellow]Once it's done, come back here and RAG-Quest is ready to go![/yellow]""",
            title="[bold]Pull Gemma 4[/bold]",
            border_style="cyan",
        )
    )
    console.input()


def startup_checks(llm_provider: str, ollama_base_url: str = "http://localhost:11434") -> None:
    """Run startup checks for configured LLM provider.
    
    For Ollama, checks if it's running and has the model.
    Prints friendly error messages if setup is needed.
    """
    if llm_provider == "ollama":
        if not check_ollama_health(ollama_base_url):
            print_ollama_setup_needed()
            return
        
        # Check if gemma4 is available
        models = get_available_ollama_models(ollama_base_url)
        has_gemma = any("gemma4" in model for model in models)
        
        if not has_gemma:
            console.print(f"\n[cyan]Available models:[/cyan] {', '.join(models) if models else 'None'}\n")
            print_ollama_model_missing()
