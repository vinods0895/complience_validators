import pytesseract
from PIL import Image

# Point to your actual Tesseract installation
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\vinod.s\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

class OCRParser:
    def parse(self, file_path: str) -> dict:
        try:
            img = Image.open(file_path).convert("L")  # grayscale
            text = pytesseract.image_to_string(img, lang="eng", config="--oem 3 --psm 6")
            return {"raw_text": text.strip()}
        except Exception as e:
            return {"raw_text": "", "error": str(e)}
