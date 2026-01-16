import pdfplumber
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\vinod.s\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

class PDFParser:
    def parse(self, file_path: str) -> dict:
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    else:
                        # fallback to OCR on page image
                        pil_img = page.to_image().original
                        text += pytesseract.image_to_string(pil_img, lang="eng", config="--oem 3 --psm 6")
            return {"raw_text": text.strip()}
        except Exception as e:
            return {"raw_text": "", "error": str(e)}
