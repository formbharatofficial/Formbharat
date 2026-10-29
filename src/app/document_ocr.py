import os
import subprocess
import tempfile
import pytesseract
from PIL import Image


_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT


def _prepare_tessdata():
    folder = os.path.join(os.environ.get("LOCALAPPDATA", ""), "FormBharat", "tessdata")
    if os.path.isfile(os.path.join(folder, "hin.traineddata")) and os.path.isfile(
        os.path.join(folder, "eng.traineddata")
    ):
        os.environ["TESSDATA_PREFIX"] = folder
    return os.environ.get("TESSDATA_PREFIX", "")


def _ocr_language():
    _prepare_tessdata()
    try:
        languages = set(pytesseract.get_languages(config=""))
    except Exception:
        return "eng"
    if "hin" in languages and "eng" in languages:
        return "hin+eng"
    if "eng" in languages:
        return "eng"
    return "eng"


def ocr_image(file_path):
    image = Image.open(file_path).convert("L")
    if max(image.size) < 1200:
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    language = _ocr_language()
    try:
        return pytesseract.image_to_string(image, lang=language).strip()
    except Exception:
        if language == "eng":
            raise
        return pytesseract.image_to_string(image, lang="eng").strip()


def ocr_pdf(file_path):
    with tempfile.TemporaryDirectory() as tmp:
        prefix = os.path.join(tmp, "page")

        subprocess.run(
            [
                "pdftoppm",
                "-jpeg",
                "-r",
                "200",
                file_path,
                prefix,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        pages = sorted(
            os.path.join(tmp, f)
            for f in os.listdir(tmp)
            if f.endswith(".jpg")
        )

        text = []

        for page in pages:
            result = ocr_image(page)
            if result:
                text.append(result)

        return "\n\n".join(text).strip()


def extract_text(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    extension = os.path.splitext(file_path)[1].lower()

    if extension in {".jpg", ".jpeg", ".png"}:
        return ocr_image(file_path)

    if extension == ".pdf":
        return ocr_pdf(file_path)

    raise ValueError(
        "Supported formats: PDF, JPG, JPEG, PNG"
    )


if __name__ == "__main__":
    print("Document OCR module: OK")
