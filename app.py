import io
from typing import Tuple
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import os

st.set_page_config(page_title="Image Resizer + Watermark", page_icon="🖼️", layout="centered")

st.title("🖼️ Image Resizer (500×500) + Watermark")
st.caption("Качи основно изображение и watermark. Резултатът е 500×500 с контрол върху позиция, мащаб и прозрачност.")

# --- SIDEBAR OPTIONS ---
st.sidebar.header("Настройки")
bg_mode = st.sidebar.selectbox("Фон на 500×500", ["Бял", "Черен", "Прозрачен (само PNG)"])
wm_scale_pct = st.sidebar.slider("Размер на watermark (% от ширината)", 5, 80, 30, 1)
wm_opacity = st.sidebar.slider("Прозрачност на watermark", 0.0, 1.0, 0.5, 0.05)
wm_margin = st.sidebar.number_input("Отстъп от ръбовете (px)", min_value=0, max_value=200, value=12, step=1)
wm_position_label = st.sidebar.selectbox(
    "Позиция на watermark",
    ["долу-ляво", "долу-център", "долу-дясно",
     "среда-ляво", "център", "среда-дясно",
     "горе-ляво", "горе-център", "горе-дясно"]
)
out_format = st.sidebar.selectbox("Формат на изхода", ["PNG", "JPEG"])

# --- FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    main_file = st.file_uploader("Качи основно изображение", type=["png", "jpg", "jpeg", "webp"])
with col2:
    wm_file = st.file_uploader("Качи watermark изображение", type=["png", "jpg", "jpeg", "webp"])

# --- DEFAULT WATERMARK ---
default_wm_path = "rsrc/marvi-logo.png"
if wm_file is not None:
    wm_img = Image.open(wm_file)
else:
    if os.path.exists(default_wm_path):
        wm_img = Image.open(default_wm_path)
        st.sidebar.info("Използва се default watermark: marvi-logo.png")
    else:
        wm_img = None
        st.sidebar.warning("Не е качен watermark и липсва default изображение.")

def pos_to_anchor(label: str) -> Tuple[str, str]:
    vmap = {
        "горе": "top", "среда": "middle", "център": "middle", "долу": "bottom"
    }
    hmap = {
        "ляво": "left", "център": "center", "дясно": "right"
    }
    parts = label.split("-")
    if len(parts) == 2:
        v, h = parts
    else:
        return ("middle", "center")
    return (vmap.get(v, "middle"), hmap.get(h, "center"))

def alpha_apply(img: Image.Image, opacity: float) -> Image.Image:
    """Приложи прозрачност към RGBA изображение."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()

    a = a.point(lambda p: int(p * opacity))
    return Image.merge("RGBA", (r, g, b, a))

def compute_xy(anchor_v: str, anchor_h: str, base_w: int, base_h: int, wm_w: int, wm_h: int, margin: int) -> Tuple[int, int]:
    if anchor_h == "left":
        x = margin
    elif anchor_h == "center":
        x = (base_w - wm_w) // 2
    else:  
        x = base_w - wm_w - margin

    if anchor_v == "top":
        y = margin
    elif anchor_v == "middle":
        y = (base_h - wm_h) // 2
    else:  # bottom
        y = base_h - wm_h - margin
    return x, y

def resize_to_square(img: Image.Image, size: int = 500, bg: str = "white", transparent: bool = False) -> Image.Image:
    """Преоразмерява изображение да се побере в size×size със запазване на пропорциите и запълване на фон."""
    if transparent:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    else:
        # bg е hex име или ('white'/'black')
        canvas = Image.new("RGB", (size, size), bg)
    # Побиране
    mode_before = img.mode
    img = ImageOps.contain(img, (size, size), method=Image.Resampling.LANCZOS)
    # Центриране
    x = (size - img.width) // 2
    y = (size - img.height) // 2
    if canvas.mode == "RGBA":
        if img.mode != "RGBA":
            img = img.convert("RGBA")
    else:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    canvas.paste(img, (x, y), img if img.mode == "RGBA" and canvas.mode == "RGBA" else None)
    return canvas

def place_watermark(base: Image.Image, wm: Image.Image, scale_pct: int, opacity: float, pos_label: str, margin: int) -> Image.Image:
    """Поставя watermark върху base (и двете в 500×500), с мащаб/прозрачност/позиция."""
    base = base.copy()
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    wm = wm.convert("RGBA")

    # resize watermark depending on scale_pct
    target_w = max(1, int(base.width * (scale_pct / 100.0)))
    scale = target_w / wm.width
    target_h = max(1, int(wm.height * scale))
    wm_resized = wm.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Apply alpaha
    wm_alpha = alpha_apply(wm_resized, opacity)

    # Apply position
    av, ah = pos_to_anchor(pos_label)
    x, y = compute_xy(av, ah, base.width, base.height, wm_alpha.width, wm_alpha.height, margin)

    base.paste(wm_alpha, (x, y), wm_alpha)
    return base

# --- MAIN UI ---
if main_file and wm_file:
    try:
        main_img = Image.open(main_file)
        wm_img = Image.open(wm_file)

        # Фон/прозрачност настройка
        bg_color = "#FFFFFF" if bg_mode == "Бял" else "#000000"
        transparent_bg = (bg_mode == "Прозрачен (само PNG)")

        # Resize main image to 500×500
        base_500 = resize_to_square(main_img, 500, bg=bg_color, transparent=transparent_bg)

        # Put the watermark on it
        composed = place_watermark(base_500, wm_img, wm_scale_pct, wm_opacity, wm_position_label, wm_margin)

        # Преглед
        st.subheader("Преглед")
        st.image(composed, caption="Готово изображение 500×500 с watermark", use_column_width=False)

        # Download  
        buf = io.BytesIO()
        save_params = {}
        if out_format == "PNG":
            fmt = "PNG"
            # If it has transparency and user wants transparent bg, keep RGBA
            if composed.mode != "RGBA" and transparent_bg:
                composed = composed.convert("RGBA")
        else:
            fmt = "JPEG"
            # JPEG dosn't support transparency
            if composed.mode != "RGB":
                composed = composed.convert("RGB")
            save_params["quality"] = 95

        composed.save(buf, format=fmt, **save_params)
        buf.seek(0)

        st.download_button(
            label=f"⬇️ Изтегли ({out_format})",
            data=buf,
            file_name=f"image_500x500_watermarked.{out_format.lower()}",
            mime=f"image/{out_format.lower()}",
        )

        # show the initial images
        with st.expander("Входни изображения"):
            c1, c2 = st.columns(2)
            with c1:
                st.image(main_img, caption="Основно изображение", use_column_width=True)
            with c2:
                st.image(wm_img, caption="Watermark", use_column_width=True)

    except Exception as e:
        st.error(f"Възникна грешка при обработката: {e}")
else:
    st.info("Качи **основно изображение** и **watermark**, за да продължиш.")
