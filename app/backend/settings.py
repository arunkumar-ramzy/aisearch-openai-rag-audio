import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("voicerag")

# Default system messages
DEFAULT_RAG_SYSTEM_MESSAGE = """
You are a helpful assistant. Only answer questions based on information you searched in the knowledge base, accessible with the 'search' tool.
The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
Never read file names or source names or keys out loud.
Always use the following step-by-step instructions to respond:
1. Always use the 'search' tool to check the knowledge base before answering a question.
2. Always use the 'report_grounding' tool to report the source of information from the knowledge base.
3. Produce an answer that's as short as possible. If the answer isn't in the knowledge base, say you don't know.
""".strip()

DEFAULT_VOICE_ASSISTANT_SYSTEM_MESSAGE = """
You are a helpful voice assistant.
The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
Provide helpful, friendly responses to the user's questions and requests.
""".strip()

# Settings file path
SETTINGS_FILE = Path(__file__).parent / "settings.json"


class Settings:
    """Settings manager for the application."""

    def __init__(self):
        self.rag_system_message: str = DEFAULT_RAG_SYSTEM_MESSAGE
        self.voice_assistant_system_message: str = DEFAULT_VOICE_ASSISTANT_SYSTEM_MESSAGE
        self._load()

    def _load(self) -> None:
        """Load settings from the settings file."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.rag_system_message = data.get("rag_system_message", DEFAULT_RAG_SYSTEM_MESSAGE)
                    self.voice_assistant_system_message = data.get(
                        "voice_assistant_system_message", DEFAULT_VOICE_ASSISTANT_SYSTEM_MESSAGE
                    )
                logger.info("Settings loaded from %s", SETTINGS_FILE)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load settings file: %s. Using defaults.", e)
        else:
            logger.info("Settings file not found. Using defaults.")

    def save(self) -> None:
        """Save settings to the settings file."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "rag_system_message": self.rag_system_message,
                        "voice_assistant_system_message": self.voice_assistant_system_message,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Settings saved to %s", SETTINGS_FILE)
        except IOError as e:
            logger.error("Failed to save settings file: %s", e)
            raise

    def get_system_message(self, rag_enabled: bool) -> str:
        """Get the appropriate system message based on mode."""
        return self.rag_system_message if rag_enabled else self.voice_assistant_system_message

    def to_dict(self) -> dict:
        """Convert settings to a dictionary."""
        return {
            "rag_system_message": self.rag_system_message,
            "voice_assistant_system_message": self.voice_assistant_system_message,
        }

    def update_from_dict(self, data: dict) -> None:
        """Update settings from a dictionary."""
        if "rag_system_message" in data:
            self.rag_system_message = data["rag_system_message"] or DEFAULT_RAG_SYSTEM_MESSAGE
        if "voice_assistant_system_message" in data:
            self.voice_assistant_system_message = (
                data["voice_assistant_system_message"] or DEFAULT_VOICE_ASSISTANT_SYSTEM_MESSAGE
            )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
