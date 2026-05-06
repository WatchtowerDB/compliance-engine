import os
import typing as t
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(
    os.getenv(
        "DJANGO_ENV_FILEPATH",
        BASE_DIR / f"env/{os.getenv('DJANGO_ENVIRONMENT', 'dev').lower()}.env",
    )
)

DEBUG: bool = bool(os.getenv("DJANGO_DEBUG"))

ALLOWED_HOSTS: list[str] = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")

CORS_ALLOWED_ORIGINS: list[str] = os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "").split(
    ","
)

CORS_ALLOW_ALL_ORIGINS: bool = (
    os.getenv("DJANGO_ENVIRONMENT", "").upper() != "PROD" and not CORS_ALLOWED_ORIGINS
)

AUTH_COOKIE_SECURE: bool = os.getenv("DJANGO_ENVIRONMENT", "").upper() == "PROD"

SECRET_KEY: str = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-dev-d6d=nm0@u_1+&f_go09c8w07-t8@z$wr*(wi(vn*$a9!bk=^o3",
)

# WARN: Database defaults to db.sqlite in nu_quran_api directory if DATABASE_URL is not set
# Refer to https://pypi.org/project/dj-database-url/ for URL schemas for different databases
DATABASES: dict[str, dj_database_url.DBConfig] = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    ),
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
