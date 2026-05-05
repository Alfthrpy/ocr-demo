from utils import clean_ocr_markdown
from ocr_engine import OCREngine
import streamlit as st
import numpy as np
from PIL import Image
import time

st.set_page_config(page_title="Demo OCR Invoice Terstruktur", layout="wide")
st.title("Demo OCR Invoice (PP-StructureV3)")
st.write("Unggah dokumen invoice untuk mengekstrak informasi dan tabelnya ke format Markdown.")


with st.sidebar:
    st.header("⚙️ Pengaturan")
    use_lite = st.toggle("Mode Cepat (Mobile Model)", value=True,
                         help="ON = lebih cepat ~3-5x, sedikit kurang akurat\nOFF = server model, lebih akurat tapi lambat")
    max_size = st.slider("Resolusi Maks (px)", 800, 3200, 1600, step=200,
                         help="Gambar di-resize sebelum diproses. Lebih kecil = lebih cepat.")


@st.cache_resource(show_spinner="Memuat model OCR...")
def get_ocr_engine(lite_mode: bool):
    return OCREngine(use_lite=lite_mode)

engine = get_ocr_engine(use_lite)

uploaded_file = st.file_uploader("Pilih gambar invoice", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    img_array_bgr = np.array(image)[:, :, ::-1].copy()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Gambar Asli")
        st.image(image, use_container_width=True)
        h, w = img_array_bgr.shape[:2]
        st.caption(f"Ukuran asli: {w}×{h}px")

    with col2:
        if st.button("Proses Ekstraksi Struktur", type="primary"):
            with st.spinner("Menganalisis layout..."):
                t0 = time.time()
                result = engine.process_image(img_array_bgr, max_size=max_size)
                elapsed = time.time() - t0

            st.success(f"✅ Selesai dalam **{elapsed:.1f} detik**")
            st.subheader("Hasil Ekstraksi (Markdown)")
            
            md_text = result.get("markdown_text", "")
            cleaned_md = clean_ocr_markdown(md_text)
            if md_text:
                st.markdown(cleaned_md, unsafe_allow_html=True)
                with st.expander("Lihat Markdown Mentah"):
                    st.code(cleaned_md, language="markdown")
            else:
                st.warning("Tidak ada teks atau struktur yang terdeteksi.")