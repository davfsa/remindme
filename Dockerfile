FROM ghcr.io/astral-sh/uv:python3.14-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image
ENV UV_PYTHON_DOWNLOADS=0

# build-base, libffi-dev and git are used to build some python modules if needed
RUN apk add --no-cache build-base git

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM docker.io/python:3.14-alpine

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

STOPSIGNAL SIGINT
ENTRYPOINT ["python", "-OO", "-m", "remindme"]
