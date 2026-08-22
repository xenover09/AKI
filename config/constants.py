"""
Application-wide constant values for AKI.

These values are static and never change at runtime. They are distinct
from `config.settings.Settings`, which holds values that MAY vary
between environments (development, production, etc.) and are sourced
from the environment or a `.env` file.
"""

from typing import Final

APP_NAME: Final[str] = "AKI"
APP_VERSION: Final[str] = "0.1.0"
APP_DESCRIPTION: Final[str] = "AKI Personal AI Operating Ecosystem"

DEFAULT_ENVIRONMENT: Final[str] = "development"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_LOG_DIR: Final[str] = "runtime/logs"
DEFAULT_LOG_FILE_NAME: Final[str] = "aki.log"

LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

LOG_FILE_MAX_BYTES: Final[int] = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT: Final[int] = 5

# ============================================================
# Intelligence layer defaults
# ============================================================

DEFAULT_AI_PROVIDER: Final[str] = "mock"
DEFAULT_AI_BASE_URL: Final[str] = "https://api.groq.com/openai/v1"
DEFAULT_AI_MODEL: Final[str] = "openai/gpt-oss-120b"
DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 60.0

AI_PROVIDER_OPENAI_COMPATIBLE: Final[str] = "openai_compatible"
AI_PROVIDER_MOCK: Final[str] = "mock"

ENV_FILE_NAME: Final[str] = ".env"
