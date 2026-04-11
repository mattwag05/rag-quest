"""Configuration management and first-run setup."""

import json
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from .engine.character import Character, CharacterClass, Race
from .engine.world import World, TimeOfDay, Weather
from .llm import LLMConfig, OpenAIProvider, OpenRouterProvider, OllamaProvider

console = Console()

CONFIG_DIR = Path.home() / ".config" / "rag-quest"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config() -> dict:
    """Get or create configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)

    return setup_first_run()


def setup_first_run() -> dict:
    """Interactive first-run setup."""
    console.clear()
    console.print(
        Panel(
            "[bold cyan]RAG-Quest[/bold cyan] - First Run Setup",
            border_style="cyan",
        )
    )

    # LLM Provider selection
    provider_config = _setup_llm_provider()

    # World setup
    world_choice = Prompt.ask(
        "\n[bold]How would you like to set up your world?[/bold]",
        choices=["1", "2", "3"],
        default="1",
    )

    world_config = {}
    if world_choice == "1":
        world_config = _setup_world_from_prompt()
    elif world_choice == "2":
        world_config = _setup_world_manual()
    else:
        world_config = _setup_world_from_lore()

    # Character creation
    character_config = _create_character()

    # Save config
    config = {
        "llm": provider_config,
        "world": world_config,
        "character": character_config,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    console.print("\n[green]Configuration saved![/green]")
    return config


def _setup_llm_provider() -> dict:
    """Setup LLM provider configuration."""
    console.print("\n[bold]LLM Provider Setup[/bold]")

    provider = Prompt.ask(
        "Select LLM provider",
        choices=["openai", "openrouter", "ollama"],
        default="openrouter",
    )

    config = {"provider": provider}

    if provider == "openai":
        config["model"] = Prompt.ask(
            "Model (e.g., gpt-4o, gpt-4-turbo)",
            default="gpt-4o",
        )
        config["api_key"] = Prompt.ask(
            "OpenAI API key",
            password=True,
        )
    elif provider == "openrouter":
        config["model"] = Prompt.ask(
            "Model (e.g., anthropic/claude-sonnet-4)",
            default="anthropic/claude-sonnet-4",
        )
        config["api_key"] = Prompt.ask(
            "OpenRouter API key",
            password=True,
        )
    else:  # ollama
        config["model"] = Prompt.ask(
            "Model (e.g., llama3.1, mistral)",
            default="llama3.1",
        )
        config["base_url"] = Prompt.ask(
            "Ollama base URL",
            default="http://localhost:11434/v1",
        )

    return config


def _setup_world_from_prompt() -> dict:
    """Setup world from a user prompt."""
    prompt = Prompt.ask(
        "Describe your ideal world (e.g., 'Dark medieval fantasy with dragon riders')"
    )

    console.print("[yellow]Note: World generation from prompts is planned for v0.2[/yellow]")

    return _setup_world_manual()


def _setup_world_manual() -> dict:
    """Manually setup world configuration."""
    world_name = Prompt.ask("World name", default="Untitled Realm")
    setting = Prompt.ask(
        "World setting",
        default="Medieval Fantasy",
    )
    tone = Prompt.ask(
        "World tone (Dark, Heroic, Whimsical, etc.)",
        default="Dark",
    )
    starting_location = Prompt.ask(
        "Starting location",
        default="A small tavern",
    )

    return {
        "name": world_name,
        "setting": setting,
        "tone": tone,
        "starting_location": starting_location,
    }


def _setup_world_from_lore() -> dict:
    """Setup world from lore files."""
    lore_path = Prompt.ask(
        "Path to lore file or directory",
        default="./lore",
    )

    # For now, just store the path
    world_config = _setup_world_manual()
    world_config["lore_path"] = lore_path

    return world_config


def _create_character() -> dict:
    """Create player character."""
    console.print("\n[bold]Character Creation[/bold]")

    name = Prompt.ask("Character name")

    # Race selection
    races = [r.value for r in Race]
    race_idx = Prompt.ask(
        "Race",
        choices=[str(i) for i in range(len(races))],
        default="0",
    )
    race = Race(races[int(race_idx)])

    # Class selection
    classes = [c.value for c in CharacterClass]
    class_idx = Prompt.ask(
        "Class",
        choices=[str(i) for i in range(len(classes))],
        default="0",
    )
    character_class = CharacterClass(classes[int(class_idx)])

    background = Prompt.ask(
        "Character background (optional, press Enter to skip)",
        default="",
    )

    return {
        "name": name,
        "race": race.name,
        "class": character_class.name,
        "background": background or None,
    }


def load_llm_provider(config: dict) -> tuple:
    """
    Load LLM provider from config.
    Returns (provider_instance, llm_config)
    """
    llm_config_dict = config["llm"]
    provider_type = llm_config_dict["provider"]

    llm_config = LLMConfig(
        provider=provider_type,
        model=llm_config_dict["model"],
        api_key=llm_config_dict.get("api_key"),
        base_url=llm_config_dict.get("base_url"),
    )

    if provider_type == "openai":
        provider = OpenAIProvider(llm_config)
    elif provider_type == "openrouter":
        provider = OpenRouterProvider(llm_config)
    elif provider_type == "ollama":
        provider = OllamaProvider(llm_config)
    else:
        raise ValueError(f"Unknown provider: {provider_type}")

    return provider, llm_config


def create_character_from_config(config: dict) -> Character:
    """Create a character from config."""
    char_config = config["character"]
    return Character(
        name=char_config["name"],
        race=Race[char_config["race"]],
        character_class=CharacterClass[char_config["class"]],
        background=char_config.get("background"),
        location=config["world"].get("starting_location", "Starting Location"),
    )


def create_world_from_config(config: dict) -> World:
    """Create a world from config."""
    world_config = config["world"]
    return World(
        name=world_config["name"],
        setting=world_config["setting"],
        tone=world_config["tone"],
    )
