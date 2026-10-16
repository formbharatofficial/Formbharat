"""Make a temporary copy that fits a form upload limit.

The saved vault file is never rewritten.
"""

import io
from pathlib import Path

from PIL import Image


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
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        payload = buffer.getvalue()
        if len(payload) <= max_bytes:
            break
        quality -= 10
    while len(payload) > max_bytes and min(image.size) > 80:
        image = image.resize((max(1, image.width // 2), max(1, image.height // 2)))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=40, optimize=True)
        payload = buffer.getvalue()
    path = Path(destination)
    path.write_bytes(payload)
    return len(payload)
