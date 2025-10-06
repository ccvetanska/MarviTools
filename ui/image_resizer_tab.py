from pathlib import Path
import io
import streamlit as st
from PIL import Image
from core.image_ops import (
    detect_colored_bbox, crop_to_bbox,
    fit_with_min_margin, paste_watermark_bottom_right
)

APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_WM = APP_DIR / "assets" / "marvi-logo.png"

def render():
    st.subheader("Обработка на изображение за продукт с поставяне на watermark")

    col_a, col_b = st.columns(2)
    with col_a:
        main_file = st.file_uploader("Качи изображение *", type=["png", "jpg", "jpeg", "webp"])
    with col_b:
        wm_file = st.file_uploader("Качи watermark (по избор)", type=["png", "jpg", "jpeg", "webp"])

    # Settings:
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        canvas_size = st.number_input("Размер на изходното изображение", min_value=100, max_value=2000, value=500, step=10)
    with col2:
        min_margin = st.number_input("Минимална рамка в px", min_value=0, max_value=200, value=30, step=1)
    with col3:
        bg_mode = st.selectbox("Фон", ["Бял", "Прозрачен"])

    opacity = st.slider("Прозрачност на watermark", 0.0, 1.0, 0.3, 0.05)

    out_format = st.selectbox("Формат за сваляне", ["PNG", "JPEG"])

    if main_file is None:
        st.info("Качи изображение, за да започнем.")
        return

    try:
        # 1) Load main image
        main_img = Image.open(main_file)

        # 2) Detect bbox of colored pixels and crop
        bbox = detect_colored_bbox(main_img)

        if bbox is None:
            st.warning("Не открих цветни пиксели (фонът изглежда изцяло бял/прозрачен). Ще използвам цялото изображение.")
        cropped = crop_to_bbox(main_img, bbox)

        # 3) Fit with the selected minimal margin
        background = "transparent" if bg_mode == "Прозрачен" else "white"
        fitted = fit_with_min_margin(cropped, canvas_size=canvas_size, min_margin=min_margin, background=background)

        # 4) Watermark – use default if not uploaded
        wm_img = None
        if wm_file is not None:
            wm_img = Image.open(wm_file)
        elif DEFAULT_WM.exists():
            wm_img = Image.open(DEFAULT_WM)

        composed = fitted
        if wm_img is not None:
            composed = paste_watermark_bottom_right(
                base_rgba=fitted, wm_img=wm_img, opacity=opacity, offset_px=5, allow_oversize=False
            )

        st.divider()
        st.subheader("Преглед")
        st.image(composed, use_container_width=False, caption="Готово изображение")

        # 5) Download button
        buf = io.BytesIO()
        if out_format == "PNG":
            # PNG supports transparency
            composed.save(buf, format="PNG")
            mime = "image/png"
            fname = "image_500x500.png"
        else:
            # JPEG supports only RGB
            composed_rgb = composed.convert("RGB")
            composed_rgb.save(buf, format="JPEG", quality=95)
            mime = "image/jpeg"
            fname = "image_500x500.jpg"

        buf.seek(0)
        st.download_button("⬇️ Свали", data=buf, file_name=fname, mime=mime)

        # Debug / info expander
        
        # with st.expander("Покажи междинните стъпки"):
        #     c1, c2 = st.columns(2)
        #     with c1:
        #         st.image(main_img, caption="Оригинал")
        #     with c2:
        #         st.image(cropped, caption="След изрязване по BBox")

        #     st.write(f"BBox: {bbox if bbox else 'N/A'}")
        #     st.write(f"Canvas: {canvas_size}×{canvas_size}, min_margin: {min_margin}px, bg: {background}")
        #     st.write("Watermark:", "default" if (wm_file is None and (DEFAULT_WM.exists())) else ("качен" if wm_file else "няма"))

        # Watermark too big warning
        if wm_img is not None:
            bw, bh = composed.size
            ww, wh = wm_img.size
            if ww + 5 > bw or wh + 5 > bh:
                st.warning("Watermark-ът е по-голям от платното и не е поставен (не променяме размера му). Ползвай по-малък watermark.")

    except Exception as e:
        st.error(f"Възникна грешка: {e}")
