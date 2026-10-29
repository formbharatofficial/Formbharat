"""Photo and signature rules for a known form.

The job title is never used. RRB and PAN keep separate sizes.
A saved vault file is not rewritten here.
"""

import os
import tempfile

from app.document_fit import fit_bounded_copy


RRB_SIGNATURE = {
    "min_bytes": 30 * 1024,
    "max_bytes": 49 * 1024,
    "min_width": 140,
    "min_height": 60,
}

PAN_PHOTO_MAX = 20 * 1024
PAN_SIGNATURE_MAX = 10 * 1024


def _check_signature(data, spec):
    if not data:
        return {"ok": False, "reason": "missing", "bytes": 0}
    handle = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    handle.close()
    try:
        return fit_bounded_copy(
            data,
            handle.name,
            max_bytes=spec["max_bytes"],
            min_bytes=spec["min_bytes"],
            min_width=spec["min_width"],
            min_height=spec["min_height"],
        )
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


def photo_guidance(board, signature_bytes=None):
    """Return Hindi lines and whether an RRB signature copy is safe to download.

    signature_bytes is the saved vault image. None means it is missing.
    """
    key = str(board or "").strip().lower()
    if key == "rrb":
        lines = [
            "फोटो इस भर्ती में अपलोड नहीं होती। आधिकारिक पेज कैमरा खोलता है। आप खुद खड़े होकर फोटो खिंचवाओगे।",
            "सफेद दीवार, गहरे कपड़े, बिना टोपी और बिना चश्मे। आँखें खुली रखो। गैलरी की पुरानी फोटो मत लगाना।",
            "दस्तखत JPG हो, 30 KB से 49 KB के बीच, कम से कम 140×60 पिक्सल। काली स्याही, जोड़कर लिखा नाम।",
        ]
        if not signature_bytes:
            lines.append("सेव दस्तखत नहीं मिली। कागज पर लिखकर स्कैन करो। असली फाइल बाद में भी नहीं बदलेगी।")
            return lines, False
        checked = _check_signature(signature_bytes, RRB_SIGNATURE)
        if checked.get("ok"):
            lines.append(
                "सेव दस्तखत की एक कॉपी "
                + str(checked["bytes"] // 1024)
                + " KB की बन सकती है। असली फाइल वैसी ही है। इस कॉपी को आधिकारिक पेज पर आप खुद चुनोगे।"
            )
            return lines, True
        if checked.get("reason") == "too_small":
            lines.append("सेव दस्तखत 140×60 पिक्सल से छोटी है। ऐप ने उसे और छोटा नहीं किया। दोबारा स्कैन करो।")
        elif checked.get("reason") == "below_minimum":
            lines.append("सेव दस्तखत 30 KB से छोटी है। ऐप ने खाली जगह जोड़कर उसे बड़ा नहीं किया। 100 DPI पर दोबारा स्कैन करो।")
        else:
            lines.append("सेव दस्तखत 30 KB और 49 KB के बीच नहीं आती। ऐप ने सीमा से बाहर की कॉपी नहीं बनाई। स्कैन दोबारा करो।")
        return lines, False
    if key == "pan":
        return [
            "पैन की फोटो JPEG है, 3.5×2.5 सेमी, ज़्यादा से ज़्यादा 20 KB।",
            "पैन का दस्तखत JPEG है, 2×4.5 सेमी, ज़्यादा से ज़्यादा 10 KB।",
            "रेलवे वाली 30–49 KB की फाइल यहाँ मत लगाना। आधिकारिक पेज पर आप खुद चुनोगे।",
        ], False
    return [
        "इस फॉर्म की फोटो और दस्तखत की साइज उसी फॉर्म की अधिसूचना में लिखी होती है।",
        "ऐप एक साइज खुद नहीं गढ़ेगा। आधिकारिक पेज पर आप खुद चुनोगे।",
    ], False
