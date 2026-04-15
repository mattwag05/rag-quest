"""Configuration management and first-run setup."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .engine.character import Character, CharacterClass, Race
from .engine.world import World
from .llm import LLMConfig, OllamaProvider, OpenAIProvider, OpenRouterProvider

console = Console()

CONFIG_DIR = Path.home() / ".config" / "rag-quest"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ============================================================================
# Configuration Manager
# ============================================================================


class ConfigManager:
    """Manages persistent configuration for RAG-Quest."""

    DEFAULT_CONFIG = {
        "version": "0.5.6",
        "llm": {
            "provider": "ollama",
            "model": "gemma4",
            "base_url": "http://localhost:11434",
            "api_key": None,
        },
        "rag": {
            "profile": "balanced",
        },
        # v0.9 — narrator memory assembler (default-on as of v0.9.1).
        # `MemoryAssembler` reads structured facts from WorldDB + LightRAG
        # lore and replaces the raw `query_world()` injection in the
        # system prompt. Profile picks the §4.2 token budgets
        # (fast/balanced/deep). Set `assembler_enabled` to `false` in
        # `~/.config/rag-quest/config.json` to restore the legacy path.
        "memory": {
            "assembler_enabled": True,
            "profile": "balanced",
        },
        "audio": {
            "tts_enabled": False,
            "tts_engine": "pyttsx3",
            "tts_voice": None,
        },
        "game": {
            "auto_save_interval": 3,
            "auto_save_slots": 3,
            "achievements_enabled": True,
            "dungeons_enabled": True,
        },
    }

    def __init__(self):
        """Initialize config manager."""
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file, env vars, or defaults.

        Priority: env vars > config file > defaults
        """
        # Check for environment variables first
        if os.getenv("LLM_PROVIDER"):
            return self._load_from_env()

        # Check for config file
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self._merge_with_defaults(config)
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not load config file: {e}[/yellow]"
                )

        # Return defaults
        return self.DEFAULT_CONFIG.copy()

    def _load_from_env(self) -> dict:
        """Load configuration from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "ollama")

        llm_config = {
            "provider": provider,
        }

        # Provider-specific model/API key
        if provider == "openai":
            llm_config["model"] = os.getenv("OPENAI_MODEL", "gpt-4o")
            llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
        elif provider == "openrouter":
            llm_config["model"] = os.getenv(
                "OPENROUTER_MODEL", "anthropic/claude-sonnet-4"
            )
            llm_config["api_key"] = os.getenv("OPENROUTER_API_KEY")
        else:  # ollama
            llm_config["model"] = os.getenv("OLLAMA_MODEL", "gemma4")
            llm_config["base_url"] = os.getenv(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            )

        rag_config = {
            "profile": os.getenv("RAG_PROFILE", "balanced"),
        }

        audio_config = {
            "tts_enabled": os.getenv("TTS_ENABLED", "false").lower() == "true",
            "tts_engine": os.getenv("TTS_ENGINE", "pyttsx3"),
            "tts_voice": os.getenv("TTS_VOICE"),
        }

        config = {
            "version": self.DEFAULT_CONFIG["version"],
            "llm": llm_config,
            "rag": rag_config,
            "audio": audio_config,
            "game": self.DEFAULT_CONFIG["game"].copy(),
        }

        return config

    def _merge_with_defaults(self, config: dict) -> dict:
        """Merge loaded config with defaults to ensure all keys exist."""
        merged = self.DEFAULT_CONFIG.copy()

        # Deep merge
        if "llm" in config:
            merged["llm"].update(config["llm"])
        if "rag" in config:
            merged["rag"].update(config["rag"])
        if "memory" in config:
            merged["memory"].update(config["memory"])
        if "audio" in config:
            merged["audio"].update(config["audio"])
        if "game" in config:
            merged["game"].update(config["game"])

        return merged

    def _save_config(self) -> None:
        """Persist configuration to ~/.config/rag-quest/config.json"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Example: config.get("llm.model")
        """
        parts = key.split(".")
        value = self.config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set and persist a configuration value using dot notation.

        Example: config.set("llm.model", "gemma4")
        """
        parts = key.split(".")
        current = self.config

        # Navigate to parent of final key
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        current[parts[-1]] = value
        self._save_config()

    def setup_wizard(self) -> dict:
        """Interactive first-run setup wizard."""
        from . import startup

        startup.print_welcome_screen()
        console.print(
            Panel(
                "[bold cyan]First-Time Setup[/bold cyan]\n\n"
                "Just a few quick choices and you'll be ready to adventure!\n"
                "This only takes a minute.",
                border_style="cyan",
            )
        )
        console.print()

        # Step 1: LLM Provider
        self.config["llm"] = self._setup_llm_provider()

        # Step 2: RAG Profile
        self.config["rag"]["profile"] = self._setup_rag_profile()

        # Step 3: TTS
        self.config["audio"]["tts_enabled"] = self._setup_tts()

        # Save config
        self._save_config()
        console.print("\n[green]✓ Configuration saved![/green]\n")

        return self.config

    def _setup_llm_provider(self) -> dict:
        """Setup LLM provider with detailed explanations."""
        console.print("\n[bold cyan]Choose Your AI Narrator[/bold cyan]")
        console.print("[dim]Where should your AI dungeon master run?[/dim]\n")

        # Show options with descriptions
        options = {
            "1": {
                "name": "Ollama (Local - Recommended)",
                "desc": "Runs completely on your computer\n         Free • Private • No internet needed • Fast with Gemma 4\n         Best for: Most players, consumer hardware, offline play",
            },
            "2": {
                "name": "OpenAI (Cloud)",
                "desc": "Uses OpenAI's GPT models via the internet\n         Requires: API key (from https://platform.openai.com)\n         Best for: Maximum quality, if you have an API subscription",
            },
            "3": {
                "name": "OpenRouter (Multi-Model Cloud)",
                "desc": "Access 100+ AI models from one place\n         Requires: API key (from https://openrouter.ai)\n         Best for: Trying different models, flexible options",
            },
        }

        for key, opt in options.items():
            console.print(f"[bold cyan][{key}][/bold cyan] {opt['name']}")
            console.print(f"    {opt['desc']}\n")

        choice = Prompt.ask(
            "Choose [1-3]",
            choices=["1", "2", "3"],
            default="1",
        )

        if choice == "1":
            return self._setup_ollama()
        elif choice == "2":
            return self._setup_openai()
        else:
            return self._setup_openrouter()

    def _setup_ollama(self) -> dict:
        """Setup Ollama provider."""
        console.print("\n[bold cyan]Ollama Setup[/bold cyan]")
        console.print("[dim]Gemma 4 is recommended (free, fast, great for D&D)[/dim]\n")

        console.print("[cyan]Popular models:[/cyan]")
        console.print(
            "  [bold]gemma4[/bold] or [bold]gemma4:latest[/bold] — Recommended (best balance)"
        )
        console.print("  [bold]gemma4:e4b[/bold] — 4B parameters (quality, needs GPU)")
        console.print(
            "  [bold]gemma4:e2b[/bold] — 2B parameters (fast, works on CPU)\n"
        )

        model = Prompt.ask(
            "Model name",
            default="gemma4",
        )

        base_url = Prompt.ask(
            "Ollama address",
            default="http://localhost:11434",
        )

        return {
            "provider": "ollama",
            "model": model,
            "base_url": base_url,
            "api_key": None,
        }

    def _setup_openai(self) -> dict:
        """Setup OpenAI provider."""
        console.print("\n[bold cyan]OpenAI Setup[/bold cyan]")
        console.print(
            "[dim]Get your API key from https://platform.openai.com/api-keys[/dim]\n"
        )

        model = Prompt.ask(
            "Model (e.g., gpt-4o, gpt-4-turbo)",
            default="gpt-4o",
        )

        while True:
            api_key = Prompt.ask(
                "API key [hidden]",
                password=True,
            )
            if not api_key:
                console.print("[yellow]API key cannot be empty.[/yellow]")
                continue
            if len(api_key) < 20:
                console.print(
                    "[yellow]API key seems too short. Paste the full key.[/yellow]"
                )
                continue
            break

        console.print("[green]✓ OpenAI configured[/green]")

        return {
            "provider": "openai",
            "model": model,
            "api_key": api_key,
            "base_url": None,
        }

    def _setup_openrouter(self) -> dict:
        """Setup OpenRouter provider."""
        console.print("\n[bold cyan]OpenRouter Setup[/bold cyan]")
        console.print("[dim]Get your API key from https://openrouter.ai/keys[/dim]\n")

        model = Prompt.ask(
            "Model (e.g., anthropic/claude-sonnet-4)",
            default="anthropic/claude-sonnet-4",
        )

        while True:
            api_key = Prompt.ask(
                "API key [hidden]",
                password=True,
            )
            if not api_key:
                console.print("[yellow]API key cannot be empty.[/yellow]")
                continue
            if len(api_key) < 20:
                console.print(
                    "[yellow]API key seems too short. Paste the full key.[/yellow]"
                )
                continue
            break

        console.print("[green]✓ OpenRouter configured[/green]")

        return {
            "provider": "openrouter",
            "model": model,
            "api_key": api_key,
            "base_url": None,
        }

    def _setup_rag_profile(self) -> str:
        """Setup RAG profile with explanations."""
        console.print("\n[bold cyan]Game Quality Setting[/bold cyan]")
        console.print("[dim]How detailed should the world-building be?[/dim]\n")

        profiles = {
            "1": {
                "name": "fast",
                "desc": "Quick & snappy. Less detailed narration.\n         Best for: Older computers, fast machines, quick testing",
            },
            "2": {
                "name": "balanced",
                "desc": "Great mix of speed and detail. ← [bold]RECOMMENDED[/bold]\n         Best for: Most players, smooth gameplay, good immersion",
            },
            "3": {
                "name": "deep",
                "desc": "Maximum detail & immersion. Slower but richer.\n         Best for: High-end hardware, patient players, deep story",
            },
        }

        for key, prof in profiles.items():
            console.print(f"[bold cyan][{key}][/bold cyan] {prof['name']}")
            console.print(f"    {prof['desc']}\n")

        choice = Prompt.ask(
            "Choose [1-3]",
            choices=["1", "2", "3"],
            default="2",
        )

        return profiles[choice]["name"]

    def _setup_tts(self) -> bool:
        """Setup Text-to-Speech."""
        console.print("\n[bold cyan]Text-to-Speech[/bold cyan]")
        console.print("[dim]Would you like the AI to read responses aloud?[/dim]")
        console.print(
            "[dim](You can toggle this anytime with /voice during gameplay)[/dim]\n"
        )

        enable = Confirm.ask("Enable TTS", default=False)
        if enable:
            console.print("[green]✓ TTS enabled[/green]")
        return enable

    def modify_settings_menu(self) -> None:
        """In-game settings modification menu."""
        while True:
            console.clear()
            console.print(Panel("[bold cyan]Settings[/bold cyan]", border_style="cyan"))

            # Show current settings
            console.print("\n[bold]Current Configuration:[/bold]\n")
            console.print(
                f"LLM Provider: [cyan]{self.config['llm']['provider']}[/cyan]"
            )
            console.print(f"Model: [cyan]{self.config['llm']['model']}[/cyan]")
            console.print(f"RAG Profile: [cyan]{self.config['rag']['profile']}[/cyan]")
            console.print(
                f"TTS: [cyan]{'Enabled' if self.config['audio']['tts_enabled'] else 'Disabled'}[/cyan]"
            )

            console.print("\n[bold]Modify:[/bold]\n")
            console.print("[cyan]1[/cyan] LLM Provider")
            console.print("[cyan]2[/cyan] Model")
            console.print("[cyan]3[/cyan] RAG Profile")
            console.print("[cyan]4[/cyan] TTS Toggle")
            console.print("[cyan]5[/cyan] Return to Game")

            choice = Prompt.ask("\nChoose setting", choices=["1", "2", "3", "4", "5"])

            if choice == "1":
                self.config["llm"] = self._setup_llm_provider()
                console.print("[green]✓ Provider updated![/green]")
                console.print("[yellow]Note: Requires restart to take effect[/yellow]")
                Prompt.ask("Press Enter to continue")
            elif choice == "2":
                model = Prompt.ask("New model name")
                self.config["llm"]["model"] = model
                self._save_config()
                console.print("[green]✓ Model updated![/green]")
                console.print("[yellow]Note: Requires restart to take effect[/yellow]")
                Prompt.ask("Press Enter to continue")
            elif choice == "3":
                self.config["rag"]["profile"] = self._setup_rag_profile()
                self._save_config()
                console.print("[green]✓ RAG profile updated![/green]")
                Prompt.ask("Press Enter to continue")
            elif choice == "4":
                self.config["audio"]["tts_enabled"] = not self.config["audio"][
                    "tts_enabled"
                ]
                self._save_config()
                status = (
                    "Enabled" if self.config["audio"]["tts_enabled"] else "Disabled"
                )
                console.print(f"[green]✓ TTS {status}![/green]")
                Prompt.ask("Press Enter to continue")
            else:
                break


# ============================================================================
# Legacy API (for backward compatibility)
# ============================================================================

_global_config_manager: Optional[ConfigManager] = None


def get_config() -> dict:
    """Get or create configuration."""
    global _global_config_manager

    # Check config file first
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)

    # Check environment variables
    if os.getenv("LLM_PROVIDER"):
        return load_config_from_env()

    # Only prompt if interactive
    if not sys.stdin.isatty():
        raise RuntimeError(
            "Configuration not found. Set LLM_PROVIDER environment variable "
            "or create a config file at ~/.config/rag-quest/config.json"
        )

    # Run setup wizard
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()

    _global_config_manager.setup_wizard()
    return _global_config_manager.config


def load_config_from_env() -> dict:
    """Load configuration from environment variables."""
    provider = os.getenv("LLM_PROVIDER", "ollama")

    llm_config = {
        "provider": provider,
    }

    if provider == "openai":
        llm_config["model"] = os.getenv("OPENAI_MODEL", "gpt-4o")
        llm_config["api_key"] = os.getenv("OPENAI_API_KEY")
    elif provider == "openrouter":
        llm_config["model"] = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
        llm_config["api_key"] = os.getenv("OPENROUTER_API_KEY")
    elif provider == "ollama":
        llm_config["model"] = os.getenv("OLLAMA_MODEL", "gemma4")
        llm_config["base_url"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    world_config = {
        "name": os.getenv("WORLD_NAME", "Generated World"),
        "setting": os.getenv("WORLD_SETTING", "Fantasy"),
        "tone": os.getenv("WORLD_TONE", "Heroic"),
        "starting_location": os.getenv("STARTING_LOCATION", "A quaint tavern"),
    }

    character_config = {
        "name": os.getenv("CHARACTER_NAME", "Adventurer"),
        "race": os.getenv("CHARACTER_RACE", "HUMAN"),
        "class": os.getenv("CHARACTER_CLASS", "WARRIOR"),
        "background": os.getenv("CHARACTER_BACKGROUND"),
    }

    rag_config = {
        "profile": os.getenv("RAG_PROFILE", "balanced"),
    }

    return {
        "llm": llm_config,
        "world": world_config,
        "character": character_config,
        "rag": rag_config,
    }


def setup_first_run() -> dict:
    """Interactive first-run setup."""
    manager = ConfigManager()
    manager.setup_wizard()
    return manager.config


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


# v0.5.0 Configuration defaults
CONFIG_DEFAULTS = {
    "saves": {
        "save_dir": None,  # Defaults to ~/.local/share/rag-quest/saves/
        "auto_save_interval": 3,  # Auto-save every 3 actions
        "auto_save_slots": 3,  # Keep 3 rotating auto-saves
    },
    "multiplayer": {
        "enabled": True,
        "mode": "local",  # "local" for hot-seat, "network" for future
    },
    "procedural_dungeons": {
        "enabled": True,
    },
    "achievements": {
        "enabled": True,
    },
}
