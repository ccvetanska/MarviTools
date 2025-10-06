from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageOps
import numpy as np

# ---------- Bounding box of the coloured pixels ----------
def _to_rgba(img: Image.Image) -> Image.Image:
    # EXIF correction (rotation) and convert to RGBA
    return ImageOps.exif_transpose(img).convert("RGBA")

def detect_colored_bbox(img: Image.Image,
                        white_thresh: int = 250,
                        alpha_thresh: int = 5) -> Optional[Tuple[int, int, int, int]]:
    """
    Finds a bounding box around the coloured pixels.
    - Background is always white (~255,255,255) or transparent.
    - A pixel is considered background if alpha <= alpha_thresh or R,G,B >= white_thresh.
    Returns (left, top, right, bottom) or None, if no coloured pixels are found.
    """
    rgba = _to_rgba(img)
    arr = np.array(rgba)  # H, W, 4
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]

    is_transparent = a <= alpha_thresh
    is_whiteish = (r >= white_thresh) & (g >= white_thresh) & (b >= white_thresh)
    is_background = is_transparent | is_whiteish
    is_colored = ~is_background

    # Mask of rows/cols that have any colored pixel
    rows = np.any(is_colored, axis=1)
    cols = np.any(is_colored, axis=0)

    if not np.any(rows) or not np.any(cols):
        return None

    top = int(np.argmax(rows))
    bottom = int(len(rows) - 1 - np.argmax(rows[::-1])) + 1  # exclusive
    left = int(np.argmax(cols))
    right = int(len(cols) - 1 - np.argmax(cols[::-1])) + 1 
    return left, top, right, bottom

def crop_to_bbox(img: Image.Image,
                 bbox: Optional[Tuple[int, int, int, int]]) -> Image.Image:
    """Cuts by bbox; if bbox is None -> returns the whole original image as RGBA."""
    if bbox is None:
        return _to_rgba(img)  # garantee RGBA and EXIF correction
    rgba = _to_rgba(img)
    return rgba.crop(bbox)

# ---------- Fit on a square 500x500 with minimal margin ----------
def fit_with_min_margin(
    img_rgba: Image.Image,
    canvas_size: int = 500,
    min_margin: int = 20,
    background: str = "white",  # "white" or "transparent"
) -> Image.Image:
    """
    Fits RGBA image in a square canvas_size x canvas_size, with at least min_margin
    margin on all sides. If the image is too large, it is scaled down to fit
    (keeping aspect ratio). The rest of the canvas is filled with the given background.
    """
    if canvas_size <= 2 * min_margin:
        raise ValueError("canvas_size трябва да е > 2 * min_margin")

    # available space for the image
    avail = canvas_size - 2 * min_margin

    # scale so that it fits in the avail x avail box
    scale = min(avail / img_rgba.width, avail / img_rgba.height)
    new_w = max(1, int(round(img_rgba.width * scale)))
    new_h = max(1, int(round(img_rgba.height * scale)))
    fitted = img_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)

    if background == "transparent":
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 255))

    # center the fitted image on the canvas
    x = (canvas_size - new_w) // 2
    y = (canvas_size - new_h) // 2
    canvas.paste(fitted, (x, y), fitted)
    return canvas

# ---------- Watermark ----------
def apply_opacity(img_rgba: Image.Image, opacity: float) -> Image.Image:
    """Applies uniform opacity to the whole image, preserving existing transparency."""
    if img_rgba.mode != "RGBA":
        img_rgba = img_rgba.convert("RGBA")
    alpha = img_rgba.getchannel("A")
    # Use point to scale alpha, but ensure rounding and clipping
    new_alpha = alpha.point(lambda p: int(p * opacity))
    img_rgba.putalpha(new_alpha)
    return img_rgba

def paste_watermark_bottom_right(
    base_rgba: Image.Image,
    wm_img: Image.Image,
    opacity: float = 0.6,
    offset_px: int = 10,
    allow_oversize: bool = False
) -> Image.Image:
    """
    Paste watermark on the down right part, with offset_px.
    If wm is bigger than the canvas and allow_oversize=False, it won't be pasted, returns original.
    """
    base = base_rgba.copy()
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    wm = _to_rgba(wm_img)

    bw, bh = base.size
    ww, wh = wm.size

    if (ww + offset_px > bw) or (wh + offset_px > bh):
        if not allow_oversize:
            # Don't paste if watermark is too big
            return base

    wm_op = apply_opacity(wm, opacity)
    x = bw - ww - offset_px
    y = bh - wh - offset_px
    base.paste(wm_op, (x, y), wm_op)
    return base
