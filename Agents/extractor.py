import os
import re
from typing import List
from utils.logger import setup_logger
from tools.pdf_parser import PDFParser
from tools.ocr_parser import OCRParser
from tools.json_parser import JSONParser
from tools.csv_parser import CSVParser
from models.invoice_model import InvoiceModel, LineItem

logger = setup_logger("ExtractorAgent", "outputs/logs/extractor.log")


class ExtractorAgent:
    """
    Unified extractor supporting:
    - JSON (multi-invoice, structured)
    - CSV (structured)
    - PDF / Images (OCR + heuristic)

    Always returns List[dict].
    """

    def __init__(self):
        self.pdf_parser = PDFParser()
        self.ocr_parser = OCRParser()
        self.json_parser = JSONParser()
        self.csv_parser = CSVParser()

    def run(self, file_path: str) -> List[dict]:
        logger.info(f"Starting extraction for {file_path}")
        ext = os.path.splitext(file_path)[1].lower()

        # ---------- JSON (MULTI-INVOICE) ----------
        if ext == ".json":
            raw = self.json_parser.parse(file_path).get("raw_data")
            invoices = self._normalize_json_batch(raw)
            logger.info(f"Extraction complete: {len(invoices)} invoices")
            return [inv.model_dump() for inv in invoices]

        # ---------- CSV ----------
        if ext == ".csv":
            raw = self.csv_parser.parse(file_path).get("raw_data", [])
            invoice = self._normalize_csv(raw)
            return [invoice.model_dump()]

        # ---------- PDF / IMAGE ----------
        text = ""

        if ext == ".pdf":
            raw = self.pdf_parser.parse(file_path)
            text = raw.get("raw_text", "")
            if not text:
                text = self.ocr_parser.parse(file_path).get("raw_text", "")

        elif ext in [".jpg", ".jpeg", ".png"]:
            text = self.ocr_parser.parse(file_path).get("raw_text", "")

        else:
            logger.warning("Unsupported file type")
            return [InvoiceModel().model_dump()]

        text = self._clean_text(text)
        invoice = self._extract_from_text(text)

        logger.info("Extraction complete (unstructured)")
        return [invoice.model_dump()]

    
    def _normalize_json_batch(self, data) -> List[InvoiceModel]:
        if not isinstance(data, list):
            raise ValueError("Expected list of invoices in JSON file")

        invoices: List[InvoiceModel] = []

        for idx, record in enumerate(data):
            try:
                invoices.append(self._normalize_single_invoice(record))
            except Exception as e:
                logger.error(f"Invoice index {idx} failed: {e}")

        return invoices

    def _normalize_single_invoice(self, data: dict) -> InvoiceModel:
        """
        Maps actual JSON invoice schema to InvoiceModel.
        """
        invoice = InvoiceModel()

       
        invoice.invoice_id = data.get("invoice_id")
        invoice.invoice_no = data.get("invoice_number")

        
        invoice.invoice_date = data.get("invoice_date")

       
        vendor = data.get("vendor", {})
        buyer = data.get("buyer", {})

        invoice.vendor_gstin = vendor.get("gstin")
        invoice.buyer_gstin = buyer.get("gstin")

        
        for item in data.get("line_items", []):
            invoice.items.append(
                LineItem(
                    description=item.get("description"),
                    quantity=item.get("quantity"),
                    unit_price=item.get("rate"),
                    line_total=item.get("amount"),
                )
            )

       
        invoice.total = data.get("total_amount")

        return invoice

    def _normalize_csv(self, rows: list) -> InvoiceModel:
        invoice = InvoiceModel()
        if not rows:
            return invoice

        first = rows[0]

        invoice.invoice_id = first.get("invoice_id")
        invoice.invoice_no = first.get("invoice_number")
        invoice.invoice_date = first.get("invoice_date")
        invoice.vendor_gstin = first.get("vendor_gstin")
        invoice.buyer_gstin = first.get("buyer_gstin")
        invoice.total = self._safe_float(first.get("total_amount"))

        for r in rows:
            invoice.items.append(
                LineItem(
                    description=r.get("description"),
                    quantity=self._safe_int(r.get("quantity")),
                    unit_price=self._safe_float(r.get("unit_price")),
                    line_total=self._safe_float(r.get("amount")),
                )
            )

        return invoice

    
    def _clean_text(self, text: str) -> str:
        ignore = [
            "thank you",
            "visit again",
            "terms and conditions",
            "authorised signatory",
        ]
        return "\n".join(
            l.strip()
            for l in text.splitlines()
            if l.strip() and not any(x in l.lower() for x in ignore)
        )

    def _extract_from_text(self, text: str) -> InvoiceModel:
        invoice = InvoiceModel()
        lines = text.splitlines()

        # For unstructured docs, invoice_number is usually present,
        # invoice_id is typically NOT available
        invoice.invoice_no = self._extract_invoice_no(lines)
        invoice.invoice_date = self._extract_date(lines)
        invoice.vendor_gstin = self._extract_gstin(lines)
        invoice.total = self._extract_total(lines)

        return invoice

    
    def _extract_invoice_no(self, lines):
        for l in lines:
            m = re.search(r"invoice\s*(no|number)[:\-]?\s*(\S+)", l, re.I)
            if m:
                return m.group(2)
        return None

    def _extract_date(self, lines):
        for l in lines:
            m = re.search(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", l)
            if m:
                return m.group(0)
        return None

    def _extract_gstin(self, lines):
        for l in lines:
            m = re.search(r"\b\d{2}[A-Z0-9]{13}\b", l)
            if m:
                return m.group(0)
        return None

    def _extract_total(self, lines):
        for l in lines:
            m = re.search(r"([\d,]+\.\d{2})", l)
            if m:
                return float(m.group(1).replace(",", ""))
        return None

    
    def _safe_float(self, v):
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return None

    def _safe_int(self, v):
        try:
            return int(v)
        except Exception:
            return None
