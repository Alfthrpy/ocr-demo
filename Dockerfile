# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — install Python deps terpisah agar layer-nya bisa di-cache
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /install

# Install build tools yang mungkin dibutuhkan beberapa C-extension
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dulu (cache layer tidak invalidated jika source code berubah)
COPY requirements-prod.txt .

# Install ke prefix /install/pkgs (bukan sistem global)
# --no-cache-dir → jaga ukuran image
# --prefix       → nanti di-copy ke stage final
RUN pip install --no-cache-dir --prefix=/install/pkgs -r requirements-prod.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — image final yang dijalankan di HF Spaces
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# ── System packages ──────────────────────────────────────────────────────────
# Diambil dari packages.txt — dibutuhkan oleh OpenCV dan PaddlePaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        # poppler-utils dibutuhkan oleh pdf2image
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# ── HuggingFace Spaces: wajib jalankan sebagai UID 1000 (non-root) ───────────
RUN useradd -m -u 1000 -s /bin/bash appuser

# ── Copy installed packages dari stage builder ────────────────────────────────
COPY --from=builder /install/pkgs /usr/local

# ── App code ──────────────────────────────────────────────────────────────────
WORKDIR /app
COPY --chown=appuser:appuser src/          ./src/
COPY --chown=appuser:appuser .streamlit/   ./.streamlit/

# ── Environment variables ─────────────────────────────────────────────────────
# Semua path model diarahkan ke /data (HF persistent bucket mount)
# storage.py juga set ini di runtime, tapi ENV di Dockerfile sebagai safety net
ENV PADDLE_HOME=/data/paddle_home \
    PPOCR_HOME=/data/paddle_home/ocr \
    CUDA_VISIBLE_DEVICES="" \
    PADDLE_DISABLE_SIGNAL_HANDLER=1 \
    FLAGS_call_stack_level=0 \
    # Supaya Python output langsung ke log HF Spaces (tidak buffered)
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Streamlit
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ── Expose port (HF Spaces selalu 7860) ──────────────────────────────────────
EXPOSE 7860

# ── Switch ke non-root user sebelum CMD ──────────────────────────────────────
USER appuser

# ── Healthcheck (opsional tapi berguna untuk monitoring) ─────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/_stcore/health')" || exit 1

# ── Entry point ───────────────────────────────────────────────────────────────
CMD ["python", "-m", "streamlit", "run", "src/app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableXsrfProtection=false", \
     "--server.maxUploadSize=20"]
