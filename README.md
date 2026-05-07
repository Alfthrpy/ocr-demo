---
title: Demo OCR Invoice Terstruktur
emoji: 🧾
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

# Demo OCR Invoice (PP-StructureV3)

Aplikasi OCR berbasis **PaddleOCR PPStructureV3** untuk mengekstrak teks dan tabel dari gambar invoice ke format Markdown terstruktur.

## 🚀 Deploy ke HuggingFace Spaces

### 1. Setup Persistent Storage (Wajib)

Karena PaddleOCR + PaddlePaddle membutuhkan ~2-3 GB disk untuk model weights,
**persistent storage bucket HARUS di-mount** sebelum app dijalankan.

Di dashboard HF Space kamu:
1. Buka tab **Settings** → **Persistent Storage**
2. Klik **Attach Persistent Storage** → pilih ukuran minimal **10 GB**
3. Mount point: `/data` ← sudah di-handle otomatis oleh `src/storage.py`

> ⚠️ Tanpa persistent storage, setiap restart Space akan re-download model (~2-3 GB) dan **akan gagal** karena 1 GB container limit.

### 2. Hardware Requirements

| Resource | Minimum | Rekomendasi |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 8 GB | 16 GB |
| Disk (container) | 1 GB (cukup) | — |
| Disk (persistent `/data`) | 10 GB | 20 GB |
| GPU | Tidak wajib | T4 untuk speed |

### 3. Struktur Path di `/data`

```
/data/
└── paddle_home/
    ├── ocr/          ← PaddleOCR model cache (PP-OCRv5)
    └── ...           ← PaddlePaddle internal cache
```

### 4. Environment Variables (auto-set oleh `storage.py`)

| Variable | Value | Keterangan |
|---|---|---|
| `PADDLE_HOME` | `/data/paddle_home` | Cache PaddlePaddle |
| `PPOCR_HOME` | `/data/paddle_home/ocr` | Cache PaddleOCR |
| `CUDA_VISIBLE_DEVICES` | `""` | Paksa CPU mode |

### 5. First Run

- **Pertama kali** deploy: model akan di-download ke `/data/paddle_home/` (~300MB untuk mobile model)
- **Restart selanjutnya**: model langsung di-load dari `/data`, startup < 30 detik

## 🛠️ Local Development

```bash
# Install dependencies
uv sync

# Run Streamlit
uv run streamlit run src/app.py
```

Saat lokal, model cache akan disimpan di `~/.cache/ocr-demo/` (bukan `/data`).

## 📁 Struktur Project

```
├── src/
│   ├── app.py          # Streamlit UI
│   ├── ocr_engine.py   # PaddleOCR wrapper
│   ├── storage.py      # HF persistent storage path manager
│   └── utils.py        # Helper functions
├── packages.txt        # System packages (apt)
├── pyproject.toml      # Python dependencies
└── .streamlit/
    └── config.toml     # Streamlit theme
```

## 📊 Performance (CPU, Mobile Model)

| Kondisi | Waktu Inference |
|---|---|
| Gambar 800px, lite mode | ~5-10 detik |
| Gambar 1600px, lite mode | ~10-20 detik |
| Gambar 1600px, server mode | ~30-60 detik |
