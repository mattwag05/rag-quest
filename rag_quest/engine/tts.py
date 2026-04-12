"""Text-to-speech narration for RAG-Quest."""

import os
from enum import Enum
from typing import Dict, Optional


class TTSEngine(Enum):
    """Available TTS engines."""

    PYTTSX3 = "pyttsx3"
    GTTS = "gtts"
    NONE = "none"


class TTSNarrator:
    """Handles text-to-speech narration for the game."""

    def __init__(
        self, enabled: bool = False, engine: str = "pyttsx3", voice_id: int = 0
    ):
        """
        Initialize TTS narrator.

        Args:
            enabled: Whether TTS is enabled
            engine: Which TTS engine to use ("pyttsx3" or "gtts")
            voice_id: Which voice to use (0 or 1 for most systems)
        """
        self.enabled = enabled
        self.engine_type = engine
        self.voice_id = voice_id
        self.engine = None
        self.voice_cache: Dict[str, str] = {}

        if enabled:
            self._initialize_engine()

    def _initialize_engine(self):
        """Initialize the selected TTS engine."""
        try:
            if self.engine_type == "pyttsx3":
                import pyttsx3

                self.engine = pyttsx3.init()

                # Set voice
                voices = self.engine.getProperty("voices")
                if self.voice_id < len(voices):
                    self.engine.setProperty("voice", voices[self.voice_id].id)

                # Set rate and volume
                self.engine.setProperty("rate", 150)  # Slightly slower for clarity
                self.engine.setProperty("volume", 0.9)

            elif self.engine_type == "gtts":
                # gtts doesn't need initialization
                self.engine = True  # Just mark as initialized

        except Exception as e:
            print(f"Failed to initialize TTS: {e}")
            self.enabled = False
            self.engine = None

    def narrate(self, text: str, narrator_type: str = "dm"):
        """
        Speak the given text.

        Args:
            text: Text to speak
            narrator_type: "dm" (dungeon master), "npc" (NPC voice), "effect" (sound effect)
        """
        if not self.enabled or not self.engine:
            return

        try:
            if self.engine_type == "pyttsx3":
                self._narrate_pyttsx3(text, narrator_type)
            elif self.engine_type == "gtts":
                self._narrate_gtts(text, narrator_type)
        except Exception as e:
            print(f"TTS narration failed: {e}")

    def _narrate_pyttsx3(self, text: str, narrator_type: str):
        """Narrate using pyttsx3."""
        if not self.engine:
            return

        # Adjust voice based on narrator type
        if narrator_type == "npc":
            # Use secondary voice for NPCs if available
            voices = self.engine.getProperty("voices")
            if len(voices) > 1:
                self.engine.setProperty("voice", voices[1 - self.voice_id].id)

        # Speak the text
        self.engine.say(text)
        self.engine.runAndWait()

        # Reset voice back to primary
        if narrator_type == "npc":
            voices = self.engine.getProperty("voices")
            self.engine.setProperty("voice", voices[self.voice_id].id)

    def _narrate_gtts(self, text: str, narrator_type: str):
        """Narrate using Google Text-to-Speech."""
        try:
            from gtts import gTTS

            # Check cache first
            if text in self.voice_cache:
                # Play cached file
                os.system(f"afplay {self.voice_cache[text]}")
                return

            # Generate new audio
            lang = "en"
            tts = gTTS(text=text, lang=lang, slow=True)

            # Save to cache
            cache_file = f"/tmp/tts_cache_{hash(text) % 100000}.mp3"
            tts.save(cache_file)
            self.voice_cache[text] = cache_file

            # Play
            os.system(f"afplay {cache_file}")

        except Exception as e:
            print(f"Google TTS failed: {e}")

    def toggle(self):
        """Toggle TTS on/off."""
        self.enabled = not self.enabled
        if self.enabled and not self.engine:
            self._initialize_engine()

    def is_enabled(self) -> bool:
        """Check if TTS is enabled."""
        return self.enabled

    def set_engine(self, engine: str):
        """Change TTS engine."""
        if engine in ["pyttsx3", "gtts"]:
            self.engine_type = engine
            self.engine = None
            if self.enabled:
                self._initialize_engine()

    def set_voice(self, voice_id: int):
        """Change voice."""
        self.voice_id = voice_id
        if self.engine_type == "pyttsx3" and self.engine:
            try:
                voices = self.engine.getProperty("voices")
                if voice_id < len(voices):
                    self.engine.setProperty("voice", voices[voice_id].id)
            except Exception:
                pass  # TTS is best-effort; a failed voice switch is non-fatal.

    def narrate_action(self, action: str, narrator: str = "Combat"):
        """Narrate a specific game action."""
        self.narrate(f"{narrator}: {action}", narrator_type="dm")

    def narrate_levelup(self, character_name: str, new_level: int):
        """Narrate a level up."""
        text = f"Level up! {character_name} is now level {new_level}!"
        self.narrate(text, narrator_type="dm")

    def narrate_victory(self, enemies_defeated: int):
        """Narrate a combat victory."""
        if enemies_defeated == 1:
            text = "Victory! You have defeated your enemy!"
        else:
            text = f"Victory! You have defeated {enemies_defeated} enemies!"
        self.narrate(text, narrator_type="dm")

    def narrate_defeat(self):
        """Narrate defeat."""
        self.narrate("You have been defeated...", narrator_type="dm")

    def clear_cache(self):
        """Clear the TTS cache."""
        for file in self.voice_cache.values():
            try:
                os.remove(file)
            except OSError:
                pass  # File already gone or unremovable — non-fatal.
        self.voice_cache.clear()

    def __del__(self):
        """Cleanup on deletion."""
        if self.engine_type == "pyttsx3" and self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass  # TTS engine may already be torn down; ignore.
        self.clear_cache()
