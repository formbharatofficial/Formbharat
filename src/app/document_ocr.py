import os
import subprocess
import tempfile
import pytesseract
from PIL import Image


def ocr_image(file_path):
    image = Image.open(file_path)
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
