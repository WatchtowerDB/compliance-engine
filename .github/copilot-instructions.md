**Project Overview**

- **Purpose:** Watchtower Compliance Engine (a Django REST API) that generates and runs compliance assertions against client schemas.
- **Layout:** source code lives under `src/` with the Django project at `src/watchtower_ce` and apps in `src/watchtower_ce/apps/`.
- **Key files:**
  - `pyproject.toml` — project metadata, `wtce` console script, Python 3.13 target, test configuration (pytest).
  - `src/manage.py` — Django management entrypoint.
  - `src/watchtower_ce/cli/` — `main.py` and `server.py` for the `wtce` CLI (the `server` command runs a Uvicorn server).
  - `src/watchtower_ce/settings/` — `base.py` and `env.py` for configuration loading via `.env`.
  - `src/watchtower_ce/apps/` — app discovery; `APPS` is auto-built in `apps/__init__.py`.

**How to run (dev)**

- Load environment variables (defaults live at `src/watchtower_ce/env/dev.env`):
  - POSIX shell:

    ```sh
    . src/watchtower_ce/env/dev.env
    ```

- Install the package and dev tools (editable):

  ```sh
  python -m pip install -e '.[dev]'
  # or use deps list: pip install -r deps/dev.requirements.txt
  ```

- Start the server (preferred CLI entrypoint defined in `pyproject.toml`):

  ```sh
  wtce server -H 127.0.0.1 -p 8000
  ```

  This runs `uvicorn` with the ASGI `application` object from `src/watchtower_ce/asgi.py`.

- Alternative Django management commands (migrations, shell, etc):

  ```sh
  python -m src.manage migrate
  python -m src.manage runserver
  ```

  (Note: prefer using `manage.py` from the `src/` layout; pytest is configured to add `src` to `PYTHONPATH`.)

**Testing & CI**

- Tests are run with `pytest`. `pyproject.toml` sets `DJANGO_SETTINGS_MODULE = watchtower_ce.settings` and `pythonpath = ["src"]`.

  ```sh
  pytest
  ```

- Dev linters/types/formatters: `ruff`, `black`, `mypy` (configured as dev extras in `pyproject.toml`).

**Important project conventions and patterns**

- `src/` layout: All imports assume `src` is on `PYTHONPATH` (pytest config reflects this).
- Dynamic app discovery: `src/watchtower_ce/apps/__init__.py` builds `APPS` by enumerating subpackages that contain an `apps.py`. Add new Django app folders (with `apps.py`) under `src/watchtower_ce/apps/` to register them automatically.
- CLI entrypoint: `pyproject.toml` exposes `wtce = "watchtower_ce.cli.main:main"`. Use the `wtce` console script after installing the package in editable mode.
- Settings and env: `src/watchtower_ce/settings/env.py` loads environment variables using `python-dotenv`; default dev env path is `src/watchtower_ce/env/dev.env`. Database config is selected from `DJANGO_ENVIRONMENT`.
- Type hints: codebase targets Python 3.13 and uses explicit typing in many modules — keep new code strongly typed when possible.

**Common patterns to follow when editing code**

- App structure: each app under `src/watchtower_ce/apps/<appname>/` should include `apps.py`, `models.py`, `views.py`, `serializers.py`, `urls.py`, and `tests.py` when applicable.
- Assertion builders: see `src/watchtower_ce/apps/compliance/assertion_builders.py` for the builder pattern and `BUILDERS` registry. Builders inherit `BaseAssertionBuilder` and implement `build(schema_json)` to return SQL assertions.
  - Example: `PCIDSSAssertionBuilder` produces (SQL, description) tuples and registers under `BUILDERS["PCI-DSS"]`.
- Migrations: Django migrations live in each app's `migrations/` subdirectory — use `python -m src.manage makemigrations` / `migrate`.

**Integration points & external dependencies**

- HTTP server: `uvicorn` (ASGI) wraps the Django ASGI app in `src/watchtower_ce/asgi.py`.
- Auth: JWT via `djangorestframework-simplejwt` (configured in `settings/base.py`).
- DB: dev default is SQLite (from `env.py`); production config expects PostgreSQL env vars.
- Schema/assertion flow: the compliance app receives schema JSON, uses `assertion_builders` to convert schemas into SQL assertions, and persists/runs results via app models and views.

**What to look for when implementing features or fixes**

- When adding a new API route, add to the app's `urls.py` and include the app in `src/watchtower_ce/apps/` so it registers. Verify `watchtower_ce/urls.py` includes the apps (`APPS` list is merged into `INSTALLED_APPS`).
- For new long-running or network code, follow existing conventions around ASGI server usage and ensure logging is compatible with `uvicorn`'s configuration.
- Tests: add unit tests to `src/watchtower_ce/apps/<app>/tests.py` and integration tests under `tests/` if appropriate; pytest picks up `test_*.py` by config.

**Gotchas & Notes discovered in the repo**

- Prefer using the `wtce` console script (defined in `pyproject.toml`) rather than `python -m watchtower_ce.cli`, because `__main__.py` may not expose a runnable `run()` symbol in the current source tree.
- Keep environment-loading behavior in mind: `env.py` uses `DJANGO_ENV_FILEPATH` if set; otherwise it defaults to `src/watchtower_ce/env/dev.env`.

**If you are the AI agent working on code changes**

- Keep edits minimal and localized. Respect the `src/` layout and `APPS` discovery mechanism.
- Update `BUILDERS` in `assertion_builders.py` if adding new frameworks (map framework name → builder class).
- Use type hints to match existing function annotations.
- Run `pytest` locally and ensure `DJANGO_SETTINGS_MODULE` remains `watchtower_ce.settings` in test runs.

If any of these areas need more detail (example workflows for containerized dev, database connection examples, or clarifying the CLI `__main__` behavior), tell me which section to expand and I will iterate.
