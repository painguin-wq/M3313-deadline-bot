# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

RUN groupadd --system --gid 1000 botuser \
    && useradd --system --uid 1000 --gid botuser --create-home botuser

COPY --from=builder /opt/venv /opt/venv
COPY --chown=botuser:botuser main.py DEADLINES.json ./

RUN mkdir -p /app/board-data \
    && chown -R botuser:botuser /app

USER botuser

STOPSIGNAL SIGINT

CMD ["python", "-u", "main.py"]
