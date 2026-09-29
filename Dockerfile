FROM python:3.12-slim-bookworm AS base
STOPSIGNAL SIGINT

# Install dependencies for locale
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    locales \
    && rm -rf /var/lib/apt/lists/* \
    && printf "en_US.UTF-8 UTF-8\nru_RU.UTF-8 UTF-8" >/etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales

FROM python:3.12-slim-bookworm
STOPSIGNAL SIGINT
WORKDIR /app

# Copy locale data from builder
COPY --from=base /usr/share/locale /usr/share/locale
COPY --from=base /etc/locale.gen /etc/locale.gen

# Create non-root user
RUN useradd -m -u 1000 botuser

# Copy Python dependencies in separate layer for better caching
COPY --chown=botuser:botuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=botuser:botuser main.py DEADLINES.json ./

USER botuser

CMD ["python3", "-u", "main.py"]
