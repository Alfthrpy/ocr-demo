"""
storage.py — Centralized path management for HuggingFace Spaces persistent storage.

HF Spaces mounts persistent bucket ke /data (bukan /tmp).
Semua model cache dan temp file diarahkan ke sini agar tidak
memenuhi 1GB container storage limit.

Usage:
    from storage import PATHS, ensure_dirs
    ensure_dirs()
"""

import os
from pathlib import Path

# ─── Detect environment ──────────────────────────────────────────────────────
# HF Spaces menyediakan /data sebagai persistent volume (bucket mount)
# Lokal → fallback ke ~/.cache/ocr-demo agar dev experience tetap konsisten
_IS_HF_SPACE = os.path.isdir("/data") or os.environ.get("SPACE_ID") is not None

if _IS_HF_SPACE:
    _BASE = Path("/data")
else:
    _BASE = Path.home() / ".cache" / "ocr-demo"

# ─── Directory layout di dalam bucket ────────────────────────────────────────
PATHS = {
    # PaddleOCR / PaddlePaddle model weights di-download ke sini
    "paddle_home":  _BASE / "paddle_home",

    # PP-OCR model cache (detection, recognition, structure)
    "ocr_models":   _BASE / "paddle_home" / "ocr",

    # Temp files untuk intermediate results (non-persistent oke)
    "tmp":          Path("/tmp") / "ocr-demo",
}

def ensure_dirs() -> None:
    """Buat semua direktori yang diperlukan jika belum ada."""
    for name, path in PATHS.items():
        path.mkdir(parents=True, exist_ok=True)

def get_env_overrides() -> dict[str, str]:
    """
    Return dict environment variable yang harus di-set sebelum
    PaddleOCR/PaddlePaddle diinisialisasi.
    Panggil os.environ.update(get_env_overrides()) di awal app.
    """
    paddle_home = str(PATHS["paddle_home"])
    return {
        # PaddlePaddle menyimpan model di $PADDLE_HOME
        "PADDLE_HOME":        paddle_home,

        # PaddleOCR juga menghormati HOME untuk menentukan cache dir
        # Override ke path bucket agar model tidak jatuh ke container /root
        "PPOCR_HOME":         str(PATHS["paddle_home"] / "ocr"),

        # Nonaktifkan telemetry / update check yang bisa gagal di sandbox
        "PADDLE_DISABLE_SIGNAL_HANDLER": "1",
        "FLAGS_call_stack_level":        "0",

        # Paksa CPU-only (HF free tier tidak ada GPU)
        "CUDA_VISIBLE_DEVICES": "",
    }

def storage_info() -> dict:
    """Return info storage yang bisa ditampilkan di Streamlit sidebar."""
    import shutil
    info = {
        "environment": "HuggingFace Spaces" if _IS_HF_SPACE else "Local Dev",
        "base_path":   str(_BASE),
        "paths":       {k: str(v) for k, v in PATHS.items()},
    }
    if _BASE.exists():
        total, used, free = shutil.disk_usage(str(_BASE))
        info["disk"] = {
            "total_gb": round(total / 1e9, 2),
            "used_gb":  round(used  / 1e9, 2),
            "free_gb":  round(free  / 1e9, 2),
        }
    return info
