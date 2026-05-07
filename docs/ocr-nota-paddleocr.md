# OCR Nota dengan PaddleOCR ‚Äî Dokumentasi Teknis

> **Scope:** Ekstraksi teks & struktur tabel dari nota (cetak maupun tulisan tangan) menggunakan PaddleOCR / PPStructureV3.

---

## Daftar Isi

1. [Konsep Dasar OCR Nota](#1-konsep-dasar-ocr-nota)
2. [Teknologi: PaddleOCR & PP-StructureV3](#2-teknologi-paddleocr--pp-structurev3)
3. [Kemampuan dan Batasan](#3-kemampuan-dan-batasan)
4. [Opsi Arsitektur Implementasi](#4-opsi-arsitektur-implementasi)
5. [Alur Flow Sistem (Pipeline Diagram)](#5-alur-flow-sistem)
6. [Contoh Implementasi](#6-contoh-implementasi)
7. [Kebutuhan Hardware](#7-kebutuhan-hardware)
8. [Deteksi Keaslian Nota](#8-deteksi-keaslian-nota)

---

## 1. Konsep Dasar OCR Nota

### 1.1 Apa itu OCR untuk Nota?

**OCR (Optical Character Recognition)** adalah proses konversi gambar teks menjadi data teks yang dapat dibaca mesin. Untuk konteks **nota/invoice**, tantangannya lebih kompleks daripada OCR dokumen biasa karena:

- Nota memiliki **layout semi-terstruktur** ‚Äî ada header, body item, dan footer total
- Ada **tabel** dengan kolom (nama item, qty, harga satuan, subtotal)
- Teks bisa berupa **cetakan thermal printer** (font monospace, low-DPI) atau **tulisan tangan**
- Kondisi gambar bervariasi: foto miring, pencahayaan buruk, kertas kusut

### 1.2 Komponen Informasi dalam Nota

Sebuah nota umumnya mengandung:

| Zona | Contoh Data |
|------|-------------|
| Header | Nama toko, alamat, nomor nota, tanggal, kasir |
| Body/Table | Item, qty, harga satuan, diskon, subtotal |
| Footer | Total, pajak (PPN), kembalian, metode bayar |
| Metadata visual | Logo, barcode, QR code |

### 1.3 Pendekatan Teknis

Ada dua level pendekatan:

```
Level 1 ‚Äî Pure OCR       : Ekstrak semua teks sebagai string mentah
Level 2 ‚Äî Structured OCR : Ekstrak + pahami layout + rekonstruksi tabel
```

Proyek ini menggunakan **Level 2** via `PPStructureV3` yang mampu memahami layout dan tabel sekaligus.

---

## 2. Teknologi: PaddleOCR & PP-StructureV3

### 2.1 Ekosistem PaddleOCR

PaddleOCR adalah framework OCR open-source dari Baidu/PaddlePaddle. Versi 3.x memperkenalkan arsitektur pipeline modular:

```
PaddleOCR
‚îú‚îÄ‚îÄ PP-OCRv5          ‚Üí Core text detection + recognition
‚îú‚îÄ‚îÄ PP-StructureV3    ‚Üí Layout analysis + table + formula + chart
‚îú‚îÄ‚îÄ PP-ChatOCRv4      ‚Üí LLM-integrated key-value extraction
‚îî‚îÄ‚îÄ TableRecognitionPipelineV2 ‚Üí Khusus tabel
```

### 2.2 PP-OCRv5 ‚Äî Core OCR Engine

PP-OCRv5 adalah versi terbaru (2024) dengan perbaikan signifikan untuk teks sulit:

#### Model yang tersedia

| Model | Ukuran | Kecepatan (GPU) | Akurasi (Hmean) | Cocok untuk |
|-------|--------|-----------------|-----------------|-------------|
| `PP-OCRv5_mobile_det` | ~3 MB | ~10ms | ~78% | CPU/edge deployment |
| `PP-OCRv5_server_det` | ~100 MB | ~89ms | **83.8%** | Server GPU |
| `PP-OCRv5_mobile_rec` | ~12 MB | ~5ms | ~78% | CPU/edge |
| `PP-OCRv5_server_rec` | ~140 MB | ~15ms | **85%+** | Server GPU |

#### Pipeline deteksi teks (PP-OCRv5)

```
Input Image
    ‚îÇ
    ‚ñº
[Pre-processing]
 - Resize (limit longest side)
 - Normalize pixel values
    ‚îÇ
    ‚ñº
[Text Detection ‚Äî DBNet++]
 - Output: polygon coordinates per text region
 - Threshold: confidence score > 0.3
    ‚îÇ
    ‚ñº
[Text Region Crop + Affine Transform]
    ‚îÇ
    ‚ñº
[Text Recognition ‚Äî SVTR / PP-LCNet]
 - CTC decoder
 - Output: string per region
    ‚îÇ
    ‚ñº
[Post-processing]
 - NMS (duplicate removal)
 - Sorting by reading order
```

### 2.3 PP-StructureV3 ‚Äî Layout & Table Pipeline

PP-StructureV3 adalah pipeline lengkap yang mengintegrasikan beberapa modul:

```
PP-StructureV3
‚îú‚îÄ‚îÄ [Doc Orientation Classify]   ‚Üí Deteksi rotasi dokumen (0¬∞/90¬∞/180¬∞/270¬∞)
‚îú‚îÄ‚îÄ [Doc Unwarping]              ‚Üí Koreksi distorsi perspektif (foto dari sudut)
‚îú‚îÄ‚îÄ [Layout Detection]           ‚Üí Segmentasi region: text/table/figure/title/list
‚îú‚îÄ‚îÄ [Text Detection]             ‚Üí PP-OCRv5 det per region
‚îú‚îÄ‚îÄ [Text Recognition]           ‚Üí PP-OCRv5 rec per text box
‚îú‚îÄ‚îÄ [Table Structure Recognition]‚Üí SLANet ‚Äî rekonstruksi HTML tabel
‚îú‚îÄ‚îÄ [Table Cell Detection]       ‚Üí Deteksi sel individual
‚îú‚îÄ‚îÄ [Formula Recognition]        ‚Üí LaTeX formula (dinonaktifkan untuk nota)
‚îî‚îÄ‚îÄ [Chart Recognition]          ‚Üí Grafik (dinonaktifkan untuk nota)
```

#### Output PP-StructureV3

Pipeline menghasilkan output dalam format Markdown yang sudah terstruktur:

```markdown
## Nama Toko ABC
Jl. Contoh No. 1 | Tel: 021-xxx

| Item | Qty | Harga | Total |
|------|-----|-------|-------|
| Kopi Susu | 2 | 15.000 | 30.000 |
| Nasi Goreng | 1 | 25.000 | 25.000 |

**TOTAL: Rp 55.000**
```

### 2.4 Model Table Recognition: SLANet

SLANet (Structure-Layout-Aware Network) adalah model khusus rekonstruksi struktur tabel:

- **Input**: Crop gambar tabel
- **Output**: HTML table string dengan colspan/rowspan
- **Keunggulan**: Mampu handle merged cells (sel yang digabung)
- **Keterbatasan**: Perlu gambar tabel yang relatif bersih

#### Versi SLANet

| Model | Bahasa | Ukuran | Akurasi TEDS |
|-------|--------|--------|--------------|
| `SLANet` | EN/Multilingual | ~9 MB | ~76% |
| `SLANet_plus` | EN/Multilingual | ~9 MB | ~76.5% |
| `SLANetV2` | Multilingual | ~15 MB | ~79%+ |

### 2.5 Layout Detection Model

Model layout detection berbasis **PicoDet** (lightweight object detector):

- Mendeteksi 6 kelas region: `text`, `title`, `figure`, `table`, `list`, `unknown`
- Backbone: LCNet (sangat ringan, cocok untuk CPU)
- Trained on: PubLayNet + CDLA dataset (dokumen akademik dan komersial)

> **Catatan penting**: Model layout dilatih dominan pada dokumen formal (paper, laporan). Untuk nota informal atau tulisan tangan, akurasi layout detection bisa menurun 10‚Äì20%.

---

## 3. Kemampuan dan Batasan

### 3.1 Kemampuan

#### Nota Cetak (Thermal/Inkjet)

| Kemampuan | Detail |
|-----------|--------|
| ‚úÖ Ekstraksi teks | Akurasi tinggi untuk font standar thermal printer |
| ‚úÖ Rekonstruksi tabel | Kolom item, qty, harga bisa diekstrak ke Markdown/HTML |
| ‚úÖ Multi-bahasa | Mendukung Indonesia, English, dan 80+ bahasa lain |
| ‚úÖ PDF & Image | Input bisa berupa JPG, PNG, PDF |
| ‚úÖ Batch processing | Bisa proses banyak file sekaligus |
| ‚úÖ Orientasi otomatis | Auto-rotate dokumen yang terbalik |
| ‚úÖ Layout segmentasi | Membedakan header, tabel, footer secara otomatis |

#### Nota Tulisan Tangan

| Kemampuan | Detail |
|-----------|--------|
| ‚ö†Ô∏è Parsial | PP-OCRv5 server model mendukung handwriting recognition |
| ‚ö†Ô∏è Tergantung kualitas | Tulisan tegak besar lebih akurat daripada tulisan miring halus |
| ‚ùå Tabel tulisan tangan | SLANet tidak dirancang untuk tabel hand-drawn |
| ‚ö†Ô∏è Angka handwritten | Lebih akurat daripada huruf, penting untuk nilai harga |

### 3.2 Batasan

#### Batasan Teknis

| Batasan | Dampak | Mitigasi |
|---------|--------|----------|
| Gambar blur/goyang | Akurasi turun drastis | Pre-processing: sharpening, deblur |
| Resolusi < 150 DPI | Banyak karakter tidak terdeteksi | Minimum 200 DPI disarankan |
| Kertas kusut/terlipat | Distorsi teks | Gunakan `use_doc_unwarping=True` |
| Cahaya tidak merata | Shadow pada teks | Pre-processing: adaptive thresholding |
| Nota sangat panjang | Memory peak tinggi | Potong gambar per zona |
| Font dekoratif/artistik | Akurasi turun 30‚Äì50% | Fine-tuning model rec |
| Tulisan tangan sambung | Hampir tidak terbaca | Perlu model khusus handwriting |

#### Batasan SLANet (Table)

```
‚úó Tidak bisa handle tabel tanpa border/garis
‚úó Merged cell yang kompleks kadang salah interpretasi
‚úó Tabel dengan background pattern (gambar di belakang tabel)
‚úó Tabel yang terputus antar halaman (multi-page table)
```

### 3.3 Akurasi Referensi (Benchmark PaddleOCR resmi)

| Skenario | Akurasi Teks | Akurasi Tabel (TEDS) |
|----------|-------------|----------------------|
| Dokumen cetak bersih | 92‚Äì96% | 76‚Äì82% |
| Foto dokumen (foto biasa) | 80‚Äì90% | 65‚Äì75% |
| Dokumen low quality | 65‚Äì80% | 50‚Äì65% |
| Tulisan tangan tegak | 70‚Äì80% | N/A |
| Tulisan tangan sambung | 30‚Äì50% | N/A |

---

## 4. Opsi Arsitektur Implementasi

Ada beberapa opsi arsitektur tergantung kebutuhan scale, latency, dan kompleksitas deployment.

---

### Arsitektur A: Monolith ó All-in-One (Paling Sederhana)

Seluruh komponen (UI, OCR engine, post-processing) berjalan dalam satu proses.

```
+----------------------------------------------+
¶               SINGLE PROCESS                 ¶
¶                                              ¶
¶  [Streamlit UI]                              ¶
¶       ¶                                      ¶
¶       ?                                      ¶
¶  [OCREngine (PPStructureV3)]                 ¶
¶       ¶                                      ¶
¶       ?                                      ¶
¶  [Post-processing / clean_ocr_markdown]      ¶
¶       ¶                                      ¶
¶       ?                                      ¶
¶  [Output: Markdown / JSON]                   ¶
+----------------------------------------------+
```

**Ini adalah arsitektur yang digunakan di repo ini sekarang.**

| Aspek | Detail |
|-------|--------|
| ? Pros | Sangat sederhana, mudah di-deploy, tidak ada network overhead |
| ? Pros | Model di-load sekali di memory (`@st.cache_resource`) |
| ? Cons | Tidak bisa scale horizontal |
| ? Cons | UI freeze jika request OCR sedang berjalan (single-thread) |
| ? Cons | Tidak bisa dipakai oleh beberapa aplikasi klien |
| ?? Cocok untuk | Demo, POC, penggunaan personal/internal satu user |

---

### Arsitektur B: Decoupled Service ó OCR sebagai REST API

OCR engine dipisahkan menjadi microservice tersendiri, UI/client memanggil via HTTP.

```
+--------------+     HTTP POST      +--------------------------------+
¶   Frontend   ¶ -----/ocr------?  ¶        OCR Service             ¶
¶  (Streamlit/ ¶                    ¶                                ¶
¶   React/etc) ¶ ?----JSON result-  ¶  [FastAPI / Flask]             ¶
+--------------+                    ¶       ¶                        ¶
                                    ¶       ?                        ¶
                +--------------+    ¶  [OCREngine]                  ¶
                ¶ Other Client ¶    ¶  (PPStructureV3)               ¶
                ¶  (Mobile App)¶    ¶       ¶                        ¶
                +--------------+    ¶       ?                        ¶
                       ¶            ¶  [Post-processing]             ¶
                       +--HTTP--?   ¶       ¶                        ¶
                                    ¶       ?                        ¶
                                    ¶  [Return JSON/Markdown]        ¶
                                    +--------------------------------+
```

**Contoh endpoint:**

```python
# FastAPI OCR Service
from fastapi import FastAPI, UploadFile
from ocr_engine import OCREngine
import numpy as np
import cv2

app = FastAPI()
engine = OCREngine(use_lite=True)  # Load sekali saat startup

@app.post("/ocr")
async def run_ocr(file: UploadFile, max_size: int = 1600):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    result = engine.process_image(image, max_size=max_size)
    return {"markdown": result["markdown_text"]}
```

| Aspek | Detail |
|-------|--------|
| ? Pros | Bisa dipakai banyak klien berbeda |
| ? Pros | OCR service bisa di-scale independen |
| ? Pros | Bisa deploy di GPU server terpisah |
| ? Cons | Ada network latency (lokal: ~1-5ms, remote bisa lebih) |
| ? Cons | Perlu mengelola dua service terpisah |
| ?? Cocok untuk | Multi-client, integrasi dengan sistem lain |

---

### Arsitektur C: Queue-based Async ó Untuk Volume Tinggi

Menggunakan message queue (Redis/RabbitMQ) untuk handle banyak request bersamaan tanpa blocking.

```
+----------+   submit job   +--------------+   queue   +-----------------+
¶  Client  ¶ -------------? ¶   API Layer  ¶ --------? ¶  Message Queue  ¶
¶          ¶                ¶  (FastAPI)   ¶           ¶  (Redis/Celery) ¶
¶          ¶ ?-- job_id --- ¶              ¶           +-----------------+
+----------+                +--------------+                    ¶ dequeue
                                                                ¶
                            +-----------------------------------?----+
                            ¶           OCR Workers (N procs)        ¶
                            ¶                                        ¶
                            ¶  Worker 1: [PPStructureV3] --? Result  ¶
                            ¶  Worker 2: [PPStructureV3] --? Result  ¶
                            ¶  Worker N: [PPStructureV3] --? Result  ¶
                            +----------------------------------------+
                                                               ¶
                            +----------------------------------?-----+
                            ¶            Result Store                ¶
                            ¶         (Redis / PostgreSQL)           ¶
                            +----------------------------------------+

Client poll GET /result/{job_id} untuk ambil hasil
```

| Aspek | Detail |
|-------|--------|
| ? Pros | Handle ratusan request bersamaan tanpa timeout |
| ? Pros | Worker bisa di-scale horizontal (tambah worker) |
| ? Pros | Klien tidak perlu tunggu (async) |
| ? Cons | Kompleksitas tinggi: perlu Redis, Celery, monitoring |
| ? Cons | Latency lebih tinggi untuk request tunggal |
| ?? Cocok untuk | Production scale, SaaS, volume > 100 nota/menit |

---

### Arsitektur D: Hybrid ó Lite Engine Lokal + Server Engine Remote

Dua engine dengan kemampuan berbeda, dipilih berdasarkan konten nota.

```
                    +-----------------------------+
                    ¶        Client App            ¶
                    ¶                             ¶
                    ¶  [Image Input]              ¶
                    ¶       ¶                     ¶
                    ¶  [Complexity Analyzer]      ¶
                    ¶   - Image quality check     ¶
                    ¶   - Handwriting detection   ¶
                    +-----------------------------+
                           ¶          ¶
                  simple   ¶          ¶  complex/handwritten
                           ¶          ¶
            +--------------?---+  +---?------------------+
            ¶  LOCAL ENGINE    ¶  ¶   REMOTE ENGINE      ¶
            ¶  (mobile model)  ¶  ¶   (server model)     ¶
            ¶  CPU-only        ¶  ¶   GPU-accelerated    ¶
            ¶  ~1-3s           ¶  ¶   ~0.3-1s            ¶
            +------------------+  +----------------------+
                    ¶                      ¶
                    +----------------------+
                               ?
                        [Merged Result]
```

| Aspek | Detail |
|-------|--------|
| ? Pros | Hemat biaya: nota mudah diproses lokal |
| ? Pros | Nota sulit mendapat akurasi terbaik dari server |
| ? Cons | Perlu logic routing yang tepat |
| ?? Cocok untuk | Aplikasi mobile/edge yang sesekali butuh akurasi tinggi |

---

### Perbandingan Ringkas Semua Arsitektur

| | A: Monolith | B: REST API | C: Queue | D: Hybrid |
|--|-------------|-------------|----------|-----------|
| Kompleksitas | ? | ?? | ???? | ??? |
| Throughput | Rendah | Sedang | Tinggi | Sedang |
| Latency | Rendah | Rendah | Sedang | Rendah |
| Scale horizontal | ? | ? | ? | Parsial |
| Cocok GPU server | Lokal | ? | ? | ? |
| Dev effort | Minimal | Sedang | Tinggi | Tinggi |

---

## 5. Alur Flow Sistem

Flow sistem untuk OCR nota dengan ekstraksi layout dan tabel (sesuai scope proyek ini):

```
+-------------------------------------------------------------------------+
¶                        INPUT STAGE                                      ¶
¶                                                                         ¶
¶  [User Upload Image/PDF]                                                ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  [Format Validation]  --- FAIL --? [Error: Format tidak didukung]      ¶
¶  (jpg/png/pdf only)                                                     ¶
+-------------------------------------------------------------------------+
                       ¶ PASS
+----------------------?--------------------------------------------------+
¶                     PRE-PROCESSING STAGE                                ¶
¶                                                                         ¶
¶  [PDF ? Image Conversion]   (jika input PDF, via pdf2image)             ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  [Resize / Downscale]                                                   ¶
¶  - max_size = 1600px (sisi terpanjang)                                  ¶
¶  - interpolation: INTER_AREA (anti-aliasing saat shrink)                ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  [BGR Array untuk OpenCV/PaddleOCR]                                     ¶
+-------------------------------------------------------------------------+
                       ¶
+----------------------?--------------------------------------------------+
¶                   PP-STRUCTUREV3 PIPELINE                               ¶
¶                                                                         ¶
¶  +------------------------------------------------------------------+   ¶
¶  ¶  MODUL 1: Document Orientation Classify  (opsional, off di repo) ¶   ¶
¶  ¶  - Prediksi rotasi: 0∞ / 90∞ / 180∞ / 270∞                      ¶   ¶
¶  ¶  - Auto-rotate jika dokumen terbalik                             ¶   ¶
¶  +------------------------------------------------------------------+   ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  +------------------------------------------------------------------+   ¶
¶  ¶  MODUL 2: Document Unwarping  (opsional, off di repo)            ¶   ¶
¶  ¶  - Koreksi perspektif dari foto sudut                            ¶   ¶
¶  ¶  - Straighten teks yang melengkung                               ¶   ¶
¶  +------------------------------------------------------------------+   ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  +------------------------------------------------------------------+   ¶
¶  ¶  MODUL 3: Layout Region Detection  (PicoDet)                     ¶   ¶
¶  ¶  - Input: full image                                             ¶   ¶
¶  ¶  - Output: bounding box per region + label                       ¶   ¶
¶  ¶    +--------------------------------------------------------+   ¶   ¶
¶  ¶    ¶  text    ¶  title   ¶  table   ¶  figure  ¶    list    ¶   ¶   ¶
¶  ¶    +--------------------------------------------------------+   ¶   ¶
¶  +------------------------------------------------------------------+   ¶
¶         ¶                                                               ¶
¶         ¶ +---------------------------------------------------------+   ¶
¶         +-?  FOR EACH "table" REGION:                               ¶   ¶
¶         ¶ ¶                                                         ¶   ¶
¶         ¶ ¶  MODUL 4A: Table Classification                         ¶   ¶
¶         ¶ ¶  - Apakah wired (bergaris) atau wireless (tanpa garis)? ¶   ¶
¶         ¶ ¶         ¶                                               ¶   ¶
¶         ¶ ¶         ?                                               ¶   ¶
¶         ¶ ¶  MODUL 4B: Table Cell Detection                         ¶   ¶
¶         ¶ ¶  - Deteksi lokasi setiap sel di dalam tabel             ¶   ¶
¶         ¶ ¶         ¶                                               ¶   ¶
¶         ¶ ¶         ?                                               ¶   ¶
¶         ¶ ¶  MODUL 4C: Table Structure Recognition (SLANet)         ¶   ¶
¶         ¶ ¶  - Rekonstruksi HTML table dengan colspan/rowspan       ¶   ¶
¶         ¶ ¶         ¶                                               ¶   ¶
¶         ¶ ¶         ?                                               ¶   ¶
¶         ¶ ¶  MODUL 4D: OCR per Sel (Text Det + Rec)                 ¶   ¶
¶         ¶ ¶  - Baca teks di setiap sel                              ¶   ¶
¶         ¶ ¶  - Output: <table><tr><td>...</td></tr></table>         ¶   ¶
¶         ¶ +---------------------------------------------------------+   ¶
¶         ¶                                                               ¶
¶         ¶ +---------------------------------------------------------+   ¶
¶         +-?  FOR EACH "text"/"title"/"list" REGION:                 ¶   ¶
¶           ¶                                                         ¶   ¶
¶           ¶  MODUL 5A: Text Detection (DBNet++ / PP-OCRv5)          ¶   ¶
¶           ¶  - Deteksi polygon setiap baris teks dalam region       ¶   ¶
¶           ¶         ¶                                               ¶   ¶
¶           ¶         ?                                               ¶   ¶
¶           ¶  MODUL 5B: Text Recognition (SVTR-LCNet / PP-OCRv5)    ¶   ¶
¶           ¶  - Crop + rectify tiap text box                         ¶   ¶
¶           ¶  - CTC decode ? string                                  ¶   ¶
¶           ¶  - Output: [{"text": "TOTAL", "conf": 0.98}, ...]       ¶   ¶
¶           +---------------------------------------------------------+   ¶
¶                                                                         ¶
+-------------------------------------------------------------------------+
                       ¶
+----------------------?--------------------------------------------------+
¶                   POST-PROCESSING STAGE                                 ¶
¶                                                                         ¶
¶  [Concatenate Markdown Pages]                                           ¶
¶  - pipeline.concatenate_markdown_pages(markdown_list)                   ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  [Clean OCR Markdown]  (clean_ocr_markdown di utils.py)                 ¶
¶  - Hapus wrapper <html><body>...</body></html>                           ¶
¶  - Hapus div kosong                                                      ¶
¶  - Normalize blank lines                                                ¶
¶         ¶                                                               ¶
¶         ?                                                               ¶
¶  [Structured Output]                                                    ¶
¶  {                                                                      ¶
¶    "markdown_text": "## Nama Toko\n\n| Item | ... |",                  ¶
¶    "images": [...]   ? embedded figures jika ada                       ¶
¶  }                                                                      ¶
+-------------------------------------------------------------------------+
                       ¶
+----------------------?--------------------------------------------------+
¶                     OUTPUT STAGE                                        ¶
¶                                                                         ¶
¶  +------------+  +------------+  +------------+  +----------------+   ¶
¶  ¶  Markdown  ¶  ¶    JSON    ¶  ¶    XLSX    ¶  ¶  HTML Table    ¶   ¶
¶  ¶  Display   ¶  ¶  (API res) ¶  ¶  (export)  ¶  ¶  (render)      ¶   ¶
¶  +------------+  +------------+  +------------+  +----------------+   ¶
+-------------------------------------------------------------------------+
```

---
## 6. Contoh Implementasi

### 6.1 Implementasi Minimal (Standalone)

```python
from paddleocr import PPStructureV3
import cv2

# Init pipeline
pipeline = PPStructureV3(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_formula_recognition=False,
    use_chart_recognition=False,
)

# Proses gambar
image = cv2.imread("nota.jpg")
output = pipeline.predict(input=image)

# Ambil markdown
markdown_pages = []
for res in output:
    markdown_pages.append(res.markdown)

full_markdown = pipeline.concatenate_markdown_pages(markdown_pages)
print(full_markdown)
```

### 6.2 Implementasi dengan Export ke XLSX (via TableRecognitionPipelineV2)

```python
from paddleocr import TableRecognitionPipelineV2

pipeline = TableRecognitionPipelineV2(device="gpu")  # pakai GPU jika ada
output = pipeline.predict("nota_dengan_tabel.jpg")

for res in output:
    res.print()                    # print ke console
    res.save_to_xlsx("./output/")  # export ke Excel
    res.save_to_html("./output/")  # export ke HTML
    res.save_to_json("./output/")  # export ke JSON
```

### 6.3 Implementasi di Repo Ini (OCREngine class)

Lihat `src/ocr_engine.py`. Class `OCREngine` membungkus `PPStructureV3` dengan:

- Toggle `use_lite` untuk pilih mobile vs server model
- Auto-resize sebelum inference (`_resize_if_needed`)
- Output berupa dict `{markdown_text, images}`

```python
from ocr_engine import OCREngine
import cv2

engine = OCREngine(use_lite=True)    # mobile model, cepat
# engine = OCREngine(use_lite=False) # server model, akurat

image = cv2.imread("nota.jpg")
result = engine.process_image(image, max_size=1600)

print(result["markdown_text"])
```

### 6.4 Visualisasi Bounding Box (draw_boxes)

```python
from utils import draw_boxes
import numpy as np
from PIL import Image

image_np = np.array(Image.open("nota.jpg"))

# structured_results format: [{"bbox": [x1,y1,x2,y2], "type": "table"}, ...]
annotated = draw_boxes(image_np, structured_results)
annotated.save("annotated_nota.jpg")
```

### 6.5 FastAPI OCR Service (Arsitektur B)

```python
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ocr_engine import OCREngine
from utils import clean_ocr_markdown
import numpy as np
import cv2

app = FastAPI(title="OCR Nota Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

# Model di-load sekali saat startup
engine = OCREngine(use_lite=False)  # Server model untuk produksi

@app.post("/ocr/nota")
async def ocr_nota(file: UploadFile, max_size: int = 1600):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(400, "Format harus JPG atau PNG")
    
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    result = engine.process_image(image, max_size=max_size)
    cleaned = clean_ocr_markdown(result["markdown_text"])
    
    return {
        "status": "success",
        "markdown": cleaned,
        "has_table": "|" in cleaned,
    }

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## 7. Kebutuhan Hardware

### 7.1 Minimum (Development / POC)

| Komponen | Minimum | Rekomendasi |
|----------|---------|-------------|
| CPU | 4-core Intel/AMD 2.0GHz | 8-core modern (Ryzen 5 / i5 Gen 10+) |
| RAM | 4 GB | 8 GB |
| Storage | 3 GB (model + env) | 5 GB |
| GPU | Tidak diperlukan | ó |
| OS | Windows 10 / Ubuntu 20.04 | Ubuntu 22.04 |

**Estimasi performa (mobile model, CPU only):**
- Nota sederhana (1 tabel kecil): **3ñ8 detik**
- Nota kompleks (multi-tabel): **10ñ20 detik**

### 7.2 Produksi ó CPU Server

| Komponen | Spesifikasi |
|----------|-------------|
| CPU | 16-core (AMD EPYC / Intel Xeon) |
| RAM | 16ñ32 GB |
| Storage | 50 GB SSD |
| GPU | Tidak diperlukan |
| Concurrency | 4ñ8 worker dengan queue |

**Estimasi performa (mobile model, 16-core CPU):**
- Throughput: **~20ñ40 nota/menit** dengan 4 worker paralel

### 7.3 Produksi ó GPU Server (Akurasi Tinggi)

| Komponen | Minimum | Optimal |
|----------|---------|---------|
| GPU | NVIDIA GTX 1060 6GB | NVIDIA RTX 3080 / A10G |
| VRAM | 4 GB | 8ñ16 GB |
| CPU | 8-core | 16-core |
| RAM | 16 GB | 32 GB |
| CUDA | 11.2+ | 12.x |

**Estimasi performa (server model, GPU):**

| GPU | Inference time (per nota) | Throughput |
|-----|--------------------------|------------|
| GTX 1060 6GB | ~0.8ñ1.5s | ~40ñ75 nota/menit |
| RTX 3080 | ~0.3ñ0.6s | ~100ñ200 nota/menit |
| A10G (cloud) | ~0.2ñ0.4s | ~150ñ300 nota/menit |

### 7.4 Setup CUDA untuk GPU

```bash
# Install PaddlePaddle GPU (CUDA 11.8)
pip install paddlepaddle-gpu==3.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

# Verify GPU terdeteksi
python -c "import paddle; print(paddle.device.get_device())"
# Expected output: gpu:0

# Jalankan engine dengan GPU
pipeline = PPStructureV3(device="gpu")
```

### 7.5 Perbandingan CPU vs GPU

| Metrik | CPU (mobile model) | CPU (server model) | GPU (server model) |
|--------|-------------------|-------------------|-------------------|
| Inference 1 nota | 3ñ8s | 15ñ30s | 0.3ñ1s |
| RAM usage | ~1.5 GB | ~3 GB | ~1.5 GB RAM + 2 GB VRAM |
| Biaya infra | Rendah | Sedang | Tinggi |
| Akurasi | ~78% | ~85% | ~85% |

> **Rekomendasi praktis:** Untuk produksi dengan volume sedang (<100 nota/jam), **CPU mobile model sudah cukup** dengan trade-off akurasi yang masih acceptable.

---

## 8. Deteksi Keaslian Nota

### 8.1 Parameter Keaslian yang Bisa Dianalisis

Setelah OCR selesai, hasil teks dapat digunakan untuk validasi keaslian nota:

#### A. Validasi Matematis

```python
def validate_nota_math(items: list[dict]) -> dict:
    """
    items: [{"name": "Kopi", "qty": 2, "price": 15000, "subtotal": 30000}, ...]
    """
    errors = []
    calculated_total = 0
    
    for item in items:
        expected = item["qty"] * item["price"]
        if abs(expected - item["subtotal"]) > 1:  # toleransi 1 rupiah (rounding)
            errors.append(f"Subtotal {item['name']} tidak cocok: {expected} vs {item['subtotal']}")
        calculated_total += item["subtotal"]
    
    return {
        "math_valid": len(errors) == 0,
        "errors": errors,
        "calculated_total": calculated_total
    }
```

**Parameter yang divalidasi:**
- `qty ◊ harga_satuan = subtotal` per item
- `S subtotal = total sebelum pajak`
- `total + PPN = grand_total`
- `grand_total - bayar = kembalian`

#### B. Validasi Format & Konsistensi

| Parameter | Cara Validasi |
|-----------|---------------|
| Nomor nota | Format regex, tidak duplikat |
| Tanggal | Dalam range yang masuk akal (tidak masa depan) |
| NPWP/NIK | Checksum digit validasi |
| Harga satuan | Tidak negatif, tidak nol untuk item berbayar |
| Nama item | Tidak mengandung karakter aneh |

#### C. Deteksi Anomali OCR (Indikator Manipulasi Digital)

```python
import re

def detect_ocr_anomalies(markdown_text: str) -> list[str]:
    anomalies = []
    
    # Karakter campuran yang tidak wajar (O vs 0, I vs 1, l vs 1)
    suspicious = re.findall(r'\b[0-9]+[OIl]+[0-9]*\b', markdown_text)
    if suspicious:
        anomalies.append(f"Karakter ambigu terdeteksi: {suspicious}")
    
    # Angka dengan desimal tidak konsisten
    prices = re.findall(r'Rp\s*([\d.,]+)', markdown_text)
    # Cek konsistensi format (semua pakai titik atau semua pakai koma)
    
    return anomalies
```

#### D. Validasi Metadata Visual (Pre-OCR)

Sebelum OCR, gambar bisa dianalisis untuk tanda-tanda manipulasi:

| Indikator | Teknik Deteksi |
|-----------|---------------|
| Copy-paste region | Error Level Analysis (ELA) dengan PIL |
| Font tidak konsisten | Analisis histogram per region |
| Garis tabel tidak lurus | Hough Transform line detection |
| Resolusi tidak wajar | DPI check + noise level analysis |
| Watermark digital | FFT spectrum analysis |

```python
from PIL import Image, ImageChops
import numpy as np

def error_level_analysis(image_path: str, quality: int = 90) -> np.ndarray:
    """ELA: area yang di-edit ulang punya error level lebih tinggi."""
    original = Image.open(image_path)
    
    # Re-save dengan kualitas tertentu
    import io
    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer)
    
    # Hitung difference
    ela_image = ImageChops.difference(original, resaved)
    ela_array = np.array(ela_image)
    
    # Area dengan nilai tinggi = potensi manipulasi
    return ela_array
```

### 8.2 Pipeline Validasi Keaslian Nota

```
[Input Nota]
     ¶
     ?
[1. Image Integrity Check]
 - ELA analysis
 - Metadata EXIF check
 - Resolution consistency
     ¶
     ?
[2. OCR Extraction] (PPStructureV3)
     ¶
     ?
[3. Structured Parsing]
 - Parse tabel ke dict
 - Extract key-value (total, tanggal, nomor)
     ¶
     ?
[4. Mathematical Validation]
 - Cek qty ◊ harga = subtotal
 - Cek S subtotal = total
 - Cek total + PPN = grand total
     ¶
     ?
[5. Format Validation]
 - Regex format nomor nota
 - Range tanggal
 - Blacklist/whitelist nama merchant
     ¶
     ?
[6. Anomaly Scoring]
 - Score 0-100: 100 = sangat mungkin asli
 - Flag jika ada anomali
     ¶
     ?
[Output: {valid: bool, score: int, flags: [...]}]
```

### 8.3 Keterbatasan Deteksi Keaslian

> **Penting:** OCR + validasi matematis TIDAK BISA mendeteksi nota palsu yang dibuat dari awal dengan angka yang konsisten. Ini hanya mendeteksi:
> - Nota yang **dimodifikasi** setelah dicetak
> - Nota dengan **kesalahan penghitungan** (baik disengaja maupun tidak)
> - Nota dengan **format tidak standar** (mencurigakan)

Untuk validasi keaslian yang lebih kuat, perlu integrasi dengan:
- **Database merchant resmi** (cross-check nomor NPWP, nama toko)
- **Sistem POS/kasir** (cross-check nomor struk)
- **QR Code / Barcode** pada nota (jika ada)

---

## Referensi

| Sumber | Link |
|--------|------|
| PaddleOCR GitHub | https://github.com/PaddlePaddle/PaddleOCR |
| PP-StructureV3 Docs | https://github.com/paddlepaddle/paddleocr/blob/main/docs/version3.x/pipeline_usage/PP-StructureV3.en.md |
| TableRecognitionV2 Docs | https://github.com/paddlepaddle/paddleocr/blob/main/docs/version3.x/pipeline_usage/table_recognition_v2.en.md |
| PP-OCRv5 Quick Start | https://github.com/paddlepaddle/paddleocr/blob/main/docs/quick_start.md |
| SLANet Paper | https://arxiv.org/abs/2203.03129 |
| PaddlePaddle GPU Install | https://www.paddlepaddle.org.cn/install/quick |

---

*Dokumen ini dibuat berdasarkan PaddleOCR v3.x dan PP-OCRv5 (2024).*
*Repo referensi: `ocr-demo` (PPStructureV3 + Streamlit)*
