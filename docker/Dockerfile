FROM nvidia/cuda:13.1.1-cudnn-devel-ubuntu24.04 AS base

# NOTE: Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV VIRTUAL_ENV="/usr/local/venv" \
  PATH="/usr/local/venv/bin:${PATH}" \
  UV_PYTHON_INSTALL_DIR="/usr/local/share/uv/python"

RUN uv venv -p 3.13 /usr/local/venv

FROM base AS build

ARG VERSION=0.0.0

ENV SETUPTOOLS_SCM_PRETEND_VERSION="${VERSION}" \
  CMAKE_ARGS="-DGGML_CUDA=on"

WORKDIR /app

RUN apt-get update && \
  apt-get install --no-install-recommends -y gcc='4:13.2.0-*' g++='4:13.2.0-*'

COPY src src/
COPY pyproject.toml uv.lock MANIFEST.in ./

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --no-install-project --frozen --active --group=ai --extra=models && \
  python src/manage.py collectstatic --noinput && \
  uv pip install .

FROM base AS runtime

ENV DJANGO_SETTINGS_MODULE=watchtower_ce.settings \
  DJANGO_DB_PATH=/home/watchtower/db.sqlite3 \
  WTCE_CHROMA_DIR=/home/watchtower/chroma \
  WTCE_EMBEDDING_MODEL_DIR=/home/watchtower/models/embedding

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

COPY --from=build /usr/local/venv /usr/local/venv

COPY --chmod=0755 ./docker/docker-entrypoint.sh /usr/local/bin/

RUN useradd -ms /usr/bin/bash watchtower && \
  apt-get update && \
  apt-get install -y --no-install-recommends tzdata && \
  rm -rf /var/lib/apt/lists/*

COPY --chown=watchtower:watchtower data/chroma_db /home/watchtower/chroma_db

USER watchtower:watchtower

RUN wtce download embedding -o /home/watchtower/models/embedding

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
