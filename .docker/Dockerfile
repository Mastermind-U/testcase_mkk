FROM python:3.14-alpine AS builder

# Copy the uv binary from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Build dependencies are only needed while wheels are being resolved/built.
RUN apk add --no-cache build-base zlib-dev

# Install third-party dependencies first so the layer is cached separately from source code.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --no-install-project --no-editable

# Install the project itself in non-editable mode so the runtime image does not need source code.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --no-editable


FROM python:3.14-alpine AS runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN addgroup -S app_user \
    && adduser -S -G app_user -h /home/app app_user

COPY --from=builder /app/.venv /app/.venv

USER app_user
