FROM nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04 AS base

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

RUN --mount=type=bind,source=.git,destination=.git \
  uv sync --active --group=ai --extra=models && \
  uv build

FROM base AS runtime

ENV DJANGO_SETTINGS_MODULE=watchtower_ce.settings

ARG SOURCE_URL=https://github.com/watchtowerdb/compliance-engine \
  VCS_REF=HEAD \
  VERSION=0.0.0 \
  LICENSE=GPL-3.0-or-later

LABEL org.opencontainers.image.title="Watchtower Compliance Engine" \
  org.opencontainers.image.description="Watchtower database compliance engine" \
  org.opencontainers.image.source="${SOURCE_URL}" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.licenses="${LICENSE}"

RUN --mount=type=bind,from=build,source=/home/watchtower/app/dist,destination=/app/dist \
  uv pip install --find-links=/app/dist watchtower-ce

COPY --chmod=0755 ./docker/docker-entrypoint.sh /usr/local/bin/

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
