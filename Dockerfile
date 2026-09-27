# ─────────────────────────────────────────────────────────────
#  IBM_BOB_2.0 — Dockerfile
#  Build:  docker build -t ibm-bob .
#  Run:    docker run --env-file .env -p 8000:8000 ibm-bob
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── System deps ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (security best practice) ───────────────────
RUN useradd --create-home --shell /bin/bash bob
WORKDIR /app

# ── Install Python dependencies first (layer-cache friendly) ─
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────────────────────
COPY agents/                          ./agents/
COPY api.py                           .
COPY main.py                          .
COPY index.html                       .

# ── Bundle the demo repo Bob analyses by default ─────────────
#    Baked into the image so Render/Fly work without volumes.
#    The default REPO_PATH in .env points here.
COPY payment/IBM-bob-payment-demo/    ./payment/IBM-bob-payment-demo/

# ── Switch to non-root ────────────────────────────────────────
RUN chown -R bob:bob /app
USER bob

# ── Expose port ───────────────────────────────────────────────
EXPOSE 8000

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# ── Start ─────────────────────────────────────────────────────
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
