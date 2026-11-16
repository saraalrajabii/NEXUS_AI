# NEXUS Backend image. Python is pinned to an exact patch version for reproducible builds.
FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first (cached layer — only rebuilt when requirements.txt changes).
# requirements.txt contains hashes, so pip refuses anything that doesn't match exactly.
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt

COPY . .

# Don't run as root inside the container.
RUN useradd --create-home --uid 1000 nexus && chown -R nexus /app
USER nexus

EXPOSE 8000
CMD ["sh", "/app/start.sh"]
