import io

from PIL import Image

from app.document_fit import fit_bounded_copy
from app.media_rules import photo_guidance


def _png(width, height, color=(20, 40, 80)):
    image = Image.new("RGB", (width, height), color)
    for x in range(0, width, 7):
        for y in range(0, height, 5):
            image.putpixel((x, y), ((x * 3) % 255, (y * 5) % 255, 90))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_small_signature_is_not_shrunk_or_padded(tmp_path):
    source = _png(160, 80)
    output = tmp_path / "copy.jpg"

    result = fit_bounded_copy(
        source,
        output,
        max_bytes=49 * 1024,
        min_bytes=30 * 1024,
        min_width=140,
        min_height=60,
    )

    assert result["ok"] is False
    assert result["reason"] == "below_minimum"
    assert output.exists() is False


def test_short_image_is_rejected_before_a_copy(tmp_path):
    output = tmp_path / "copy.jpg"
    result = fit_bounded_copy(
        _png(100, 40),
        output,
        max_bytes=49 * 1024,
        min_bytes=30 * 1024,
        min_width=140,
        min_height=60,
    )

    assert result["reason"] == "too_small"
    assert output.exists() is False


def test_copy_stays_inside_the_byte_band(tmp_path):
    output = tmp_path / "copy.jpg"
    result = fit_bounded_copy(
        _png(900, 400),
        output,
        max_bytes=80 * 1024,
        min_bytes=1000,
        min_width=140,
        min_height=60,
    )

    assert result["ok"] is True
    assert 1000 <= result["bytes"] <= 80 * 1024
    assert output.read_bytes().startswith(b"\xff\xd8\xff")
    assert result["width"] >= 140
    assert result["height"] >= 60


def test_rrb_photo_stays_on_the_camera_and_a_tiny_signature_is_not_ready():
    lines, ready = photo_guidance("rrb", _png(160, 80))

    assert ready is False
    assert any("कैमरा" in line for line in lines)
    assert any("30 KB" in line for line in lines)
    assert any("छोटी" in line for line in lines)


def test_rrb_without_a_signature_does_not_offer_a_copy():
    lines, ready = photo_guidance("rrb", None)

    assert ready is False
    assert any("नहीं मिली" in line for line in lines)


def test_pan_size_is_separate_from_the_railway_file():
    lines, ready = photo_guidance("pan", _png(400, 300))

    assert ready is False
    assert any("20 KB" in line for line in lines)
    assert any("10 KB" in line for line in lines)
    assert any("रेलवे" in line for line in lines)


def test_an_unknown_form_does_not_invent_a_size():
    lines, ready = photo_guidance("none", None)

    assert ready is False
    assert any("खुद नहीं गढ़ेगा" in line for line in lines)
