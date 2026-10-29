"""Make a temporary copy that fits a form upload limit.

The saved vault file is never rewritten.
"""

import io
from pathlib import Path

from PIL import Image


def _jpeg(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def fit_image_copy(data, destination, max_width=900, max_height=900, max_bytes=300 * 1024):
    """Write a smaller JPEG copy. Return the new size in bytes."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("image data is required")
    image = Image.open(io.BytesIO(bytes(data)))
    image = image.convert("RGB")
    image.thumbnail((max_width, max_height))
    quality = 85
    payload = b""
    while quality >= 35:
        payload = _jpeg(image, quality)
        if len(payload) <= max_bytes:
            break
        quality -= 10
    while len(payload) > max_bytes and min(image.size) > 80:
        image = image.resize((max(1, image.width // 2), max(1, image.height // 2)))
        payload = _jpeg(image, 40)
    path = Path(destination)
    path.write_bytes(payload)
    return len(payload)


def fit_bounded_copy(data, destination, max_bytes, min_bytes=1, min_width=1, min_height=1):
    """Write a JPEG copy inside a size band. Never invent pixels or pad a small file.

    Returns ok False and writes nothing when the picture is below the
    minimum pixels, or when shrinking it would fall under min_bytes.
    """
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("image data is required")
    if min_bytes < 1 or max_bytes < min_bytes:
        raise ValueError("byte limits are invalid")
    image = Image.open(io.BytesIO(bytes(data)))
    image = image.convert("RGB")
    width, height = image.size
    if width < min_width or height < min_height:
        return {"ok": False, "reason": "too_small", "bytes": 0, "width": width, "height": height}

    scale = 1.0
    for _ in range(30):
        current_width = max(1, int(round(image.width * scale)))
        current_height = max(1, int(round(image.height * scale)))
        if current_width < min_width or current_height < min_height:
            break
        current = image
        if (current_width, current_height) != image.size:
            current = image.resize((current_width, current_height), Image.Resampling.LANCZOS)
        high = _jpeg(current, 95)
        if len(high) < min_bytes:
            return {
                "ok": False,
                "reason": "below_minimum",
                "bytes": len(high),
                "width": current_width,
                "height": current_height,
            }
        for quality in range(95, 34, -5):
            payload = high if quality == 95 else _jpeg(current, quality)
            size = len(payload)
            if min_bytes <= size <= max_bytes:
                Path(destination).write_bytes(payload)
                return {
                    "ok": True,
                    "reason": "ready",
                    "bytes": size,
                    "width": current_width,
                    "height": current_height,
                }
            if size < min_bytes:
                break
        scale *= 0.9
    return {"ok": False, "reason": "cannot_fit", "bytes": 0, "width": width, "height": height}
