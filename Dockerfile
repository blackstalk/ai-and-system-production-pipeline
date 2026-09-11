# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# Install dependencies in a separate layer so code-only changes don't
# invalidate the dependency cache.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Run as a non-root user — a baseline hardening step the AI reviewer
# and Bandit both expect in a production Dockerfile.
RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 8000

# DEPLOYMENT_TRACK is overridden per-container by docker-compose.yml to
# simulate stable vs. canary instances. See docs/deployment-strategy.md.
ENV DEPLOYMENT_TRACK=stable

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
