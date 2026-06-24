# USAi Chat — container image (Infrastructure as Code).
#
# WHY: docs/principles.md §3 — running the app should be DECLARATIVE and
# REPRODUCIBLE, not a list of manual steps. This image is dev/deploy tooling
# (per §1, Docker ships nothing INTO the app); the container's runtime surface is
# still only the Python stdlib + python-dotenv.
#
# Build & run via the Makefile / docker-compose (preferred), or directly:
#   docker build -t usai-chat .
#   docker run --rm -p 8000:8000 --env-file .env usai-chat
#
# Pinned to a slim, current Python. server.py runs on 3.9+; we use a modern 3.x
# here for security patches (the code is version-tolerant).
FROM python:3.12-slim

# Don't write .pyc files; stream stdout/stderr so logs appear immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user — never run a network-facing service as root (DevSecOps).
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

# Install ONLY the runtime dependency first for better layer caching.
# requirements.txt is the single source of truth for runtime deps (python-dotenv).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy just the files the running app needs (keeps the image minimal & auditable).
# .env is intentionally NOT copied — it's provided at run time via --env-file /
# compose env_file, so secrets never bake into the image.
COPY server.py index.html app.js styles.css ./

USER appuser
EXPOSE 8000

# Liveness check using /config — fast, no secrets, no vault I/O.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/config', timeout=2).status==200 else 1)"

CMD ["python", "server.py"]
