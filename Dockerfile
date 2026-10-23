# The whole simulator in one image: the API and the built page on one port.
#   docker run --rm -p 8000:8000 ghcr.io/acevizli/tunnelsimulator   -> http://localhost:8000

# 1. Build the page. Runs on the build machine's own platform: the output is plain JS, the same for every target.
FROM --platform=$BUILDPLATFORM node:22.11.0-slim AS page
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# 2. Python core + server, with the page copied in next to them.
FROM python:3.12.8-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first, so editing the code doesn't reinstall numpy and friends
COPY pyproject.toml uv.lock .python-version ./
COPY core/pyproject.toml core/
COPY server/pyproject.toml server/
RUN uv sync --frozen --no-dev --no-install-workspace

COPY core core
COPY server server
COPY scenarios scenarios
RUN uv sync --frozen --no-dev
COPY --from=page /web/dist web/dist

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "tunnelsim_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
