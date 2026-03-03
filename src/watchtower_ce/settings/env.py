import os
import typing as t
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    os.getenv(
        "DJANGO_ENV_FILEPATH",
        BASE_DIR / f"env/{os.getenv('DJANGO_ENVIRONMENT', 'dev').lower()}.env",
    )
)

DEBUG: bool = bool(os.getenv("DJANGO_DEBUG"))

ALLOWED_HOSTS: list[str] = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")

CORS_ALLOW_ALL_ORIGINS: bool = os.getenv("DJANGO_ENVIRONMENT", "").upper() != "PROD"

SECRET_KEY: str = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-dev-d6d=nm0@u_1+&f_go09c8w07-t8@z$wr*(wi(vn*$a9!bk=^o3",
)

_DB_CONFIG: dict[str, dict[str, str | Path]] = {
    "DEV": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    },
    "PROD": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("DJANGO_DB_HOST", "localhost"),
        "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
        "NAME": os.getenv("DJANGO_DB_NAME", "watchtower_ce"),
        "USER": os.getenv("DJANGO_DB_USER", ""),
        "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", ""),
    },
}

DATABASES: dict[str, dict[str, str | Path]] = {
    "default": _DB_CONFIG.get(
        os.getenv("DJANGO_ENVIRONMENT", "").upper(), _DB_CONFIG["DEV"]
    )
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

BASE_MODEL_PATH: t.Optional[Path] = (
    Path(os.environ["WTCE_BASE_MODEL_PATH"])
    if os.getenv("WTCE_BASE_MODEL_PATH")
    else None
)
CHROMA_DIR: t.Optional[Path] = (
    Path(os.environ["WTCE_CHROMA_DIR"]) if os.getenv("WTCE_CHROMA_DIR") else None
)
EMBEDDING_MODEL_DIR: t.Optional[Path] = (
    Path(os.environ["WTCE_EMBEDDING_MODEL_DIR"])
    if os.getenv("WTCE_EMBEDDING_MODEL_DIR")
    else None
)
