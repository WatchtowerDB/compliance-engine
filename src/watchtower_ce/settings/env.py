import os
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
CELERY_STALE_PROCESS_TIMEOUT: int = int(os.getenv("CELERY_STALE_PROCESS_TIMEOUT", "15"))
CELERY_STALE_PENDING_PROCESS_TIMEOUT: int = int(
    os.getenv("CELERY_STALE_PENDING_PROCESS_TIMEOUT", "120")
)

# Mock compliance checker settings
USE_MOCK_COMPLIANCE_CHECKER: bool = (
    os.getenv("WTCE_USE_MOCK_COMPLIANCE_CHECKER", "false").lower() == "true"
)
SUPPRESS_MOCK_COMPLIANCE_CHECKER_WARNING: bool = (
    os.getenv("WTCE_SUPPRESS_MOCK_COMPLIANCE_CHECKER_WARNING", "false").lower()
    == "true"
)
MOCK_ARTIFICIAL_STREAMING_DELAY: float = float(
    os.getenv("WTCE_MOCK_ARTIFICIAL_STREAMING_DELAY", "0.1")
)
MOCK_ARTIFICIAL_PROCESSING_DELAY: float = float(
    os.getenv("WTCE_MOCK_ARTIFICIAL_PROCESSING_DELAY", "7")
)
LLM_MAX_PARSE_RETRIES: int = int(os.getenv("WTCE_LLM_MAX_PARSE_RETRIES", "3"))
LLM_SERVER_URL: str = os.getenv("WTCE_LLM_SERVER_URL", "http://127.0.0.1:6767")

WTVS_SERVER_URL: str = os.getenv("WTCE_WTVS_SERVER_URL", "http://localhost:7777")
