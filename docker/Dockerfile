FROM python:3.13-slim AS base

# NOTE: Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN useradd -ms /usr/bin/bash watchtower

USER watchtower:watchtower

WORKDIR /home/watchtower

RUN uv venv -p 3.13 .venv

ENV VIRTUAL_ENV=/home/watchtower/.venv \
    PATH=/home/watchtower/.venv/bin:${PATH}

FROM base AS build

WORKDIR /home/watchtower/app

USER root:root

RUN apt-get update \
    && apt-get install --no-install-recommends -y git='1:2.47.3-*'

COPY src ./src
COPY pyproject.toml uv.lock ./

RUN --mount=type=bind,source=.git,destination=.git uv sync --active \
    && uv build

FROM base AS runtime

ENV DJANGO_SETTINGS_MODULE=watchtower_ce.settings

RUN --mount=type=bind,from=build,source=/home/watchtower/app/dist,destination=/app/dist uv pip install --find-links=/app/dist watchtower-ce

COPY --chmod=0755 ./docker/docker-entrypoint.sh /usr/local/bin/

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
