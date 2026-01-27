import os
import re
import json
from typing import List, Callable, Optional
from datetime import datetime, date

from utils.logger import setup_logger
from tools.pdf_parser import PDFParser
from tools.ocr_parser import OCRParser
from tools.json_parser import JSONParser
from tools.csv_parser import CSVParser
from models.invoice_model import InvoiceModel, LineItem, Vendor, Buyer

logger = setup_logger("ExtractorAgent", "outputs/logs/extractor.log")


class ExtractorAgent:
    """
    Unified extractor agent supporting:
    - JSON (multi-invoice, structured)
    - CSV (structured)
    - PDF / Images (OCR + heuristics + optional LLM assist)

    Always returns List[dict].
    """

    def __init__(self, llm: Optional[Callable[[str], str]] = None):
        self.pdf_parser = PDFParser()
        self.ocr_parser = OCRParser()
        self.json_parser = JSONParser()
        self.csv_parser = CSVParser()
        self.llm = llm

  
    # PUBLIC ENTRY
     

    def run(self, file_path: str) -> List[dict]:
        logger.info(f"Starting extraction for {file_path}")
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            raw = self.json_parser.parse(file_path).get("raw_data")
            invoices = self._normalize_json_batch(raw)
            logger.info(f"Extraction complete: {len(invoices)} invoices")
            return [inv.model_dump() for inv in invoices]

        if ext == ".csv":
            raw = self.csv_parser.parse(file_path).get("raw_data", [])
            invoice = self._normalize_csv(raw)
            return [invoice.model_dump()]

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

        if self.llm:
            invoice = self._llm_assist(text, invoice)

        logger.info("Extraction complete (unstructured)")
        return [invoice.model_dump()]

    # JSON NORMALIZATION
   

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
        invoice = InvoiceModel()

        invoice.invoice_id = data.get("invoice_id")
        invoice.invoice_number = data.get("invoice_number")
        invoice.invoice_date = self._parse_date(data.get("invoice_date"))
        invoice.subtotal = data.get("subtotal")
        invoice.total_tax = data.get("total_tax")
        invoice.total_amount = data.get("total_amount")
        invoice.irn = data.get("irn")
        invoice.irn_date = self._parse_date(data.get("irn_date"))
        invoice.qr_code_present = data.get("qr_code_present")
        invoice.payment_terms = data.get("payment_terms")
        invoice.po_reference = data.get("po_reference")
        invoice.notes = data.get("notes")

        vendor = data.get("vendor", {})
        invoice.vendor = Vendor(
            name=vendor.get("name"),
            gstin=vendor.get("gstin"),
            pan=vendor.get("pan"),
            address=vendor.get("address"),
        )

        buyer = data.get("buyer", {})
        invoice.buyer = Buyer(
            name=buyer.get("name"),
            gstin=buyer.get("gstin"),
            address=buyer.get("address"),
        )

        for item in data.get("line_items", []):
            invoice.line_items.append(
                LineItem(
                    description=item.get("description"),
                    hsn_sac=item.get("hsn_sac"),
                    quantity=item.get("quantity"),
                    unit=item.get("unit"),
                    rate=item.get("rate"),
                    amount=item.get("amount"),
                    cgst_rate=item.get("cgst_rate"),
                    sgst_rate=item.get("sgst_rate"),
                    igst_rate=item.get("igst_rate"),
                    cgst_amount=item.get("cgst_amount"),
                    sgst_amount=item.get("sgst_amount"),
                    igst_amount=item.get("igst_amount"),
                )
            )

        invoice.cgst_rate = data.get("cgst_rate")
        invoice.cgst_amount = data.get("cgst_amount")
        invoice.sgst_rate = data.get("sgst_rate")
        invoice.sgst_amount = data.get("sgst_amount")
        invoice.igst_rate = data.get("igst_rate")
        invoice.igst_amount = data.get("igst_amount")

        return invoice

    # CSV NORMALIZATION
    

    def _normalize_csv(self, rows: list) -> InvoiceModel:
        invoice = InvoiceModel()
        if not rows:
            return invoice

        first = rows[0]
        invoice.invoice_id = first.get("invoice_id")
        invoice.invoice_number = first.get("invoice_number")
        invoice.invoice_date = self._parse_date(first.get("invoice_date"))
        invoice.subtotal = self._safe_float(first.get("subtotal"))
        invoice.total_tax = self._safe_float(first.get("total_tax"))
        invoice.total_amount = self._safe_float(first.get("total_amount"))
        invoice.irn = first.get("irn")
        invoice.irn_date = self._parse_date(first.get("irn_date"))
        invoice.qr_code_present = first.get("qr_code_present") in ("true", "True", "1")
        invoice.payment_terms = first.get("payment_terms")
        invoice.po_reference = first.get("po_reference")
        invoice.notes = first.get("notes")

        invoice.vendor = Vendor(
            name=first.get("vendor_name"),
            gstin=first.get("vendor_gstin"),
            pan=first.get("vendor_pan"),
            address=first.get("vendor_address"),
        )

        invoice.buyer = Buyer(
            name=first.get("buyer_name"),
            gstin=first.get("buyer_gstin"),
            address=first.get("buyer_address"),
        )

        for r in rows:
            invoice.line_items.append(
                LineItem(
                    description=r.get("description"),
                    hsn_sac=r.get("hsn_sac"),
                    quantity=self._safe_int(r.get("quantity")),
                    unit=r.get("unit"),
                    rate=self._safe_float(r.get("rate")),
                    amount=self._safe_float(r.get("amount")),
                    cgst_rate=self._safe_float(r.get("cgst_rate")),
                    sgst_rate=self._safe_float(r.get("sgst_rate")),
                    igst_rate=self._safe_float(r.get("igst_rate")),
                    cgst_amount=self._safe_float(r.get("cgst_amount")),
                    sgst_amount=self._safe_float(r.get("sgst_amount")),
                    igst_amount=self._safe_float(r.get("igst_amount")),
                )
            )

        return invoice

     
    # UNSTRUCTURED EXTRACTION
     

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

        invoice.invoice_number = self._extract_invoice_no(lines)
        invoice.invoice_date = self._parse_date(self._extract_date(lines))
        gstin = self._extract_gstin(lines)
        if gstin:
            invoice.vendor = Vendor(gstin=gstin)
        invoice.total_amount = self._extract_total(lines)

        return invoice

     
    # DATE NORMALIZATION (FIX)
     

    def _parse_date(self, value) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue
        return None

     
    # LLM ASSIST
     

    def _llm_assist(self, text: str, invoice: InvoiceModel) -> InvoiceModel:
        missing = []

        if not invoice.invoice_number:
            missing.append("invoice_number")
        if not invoice.invoice_date:
            missing.append("invoice_date")
        if not invoice.total_amount:
            missing.append("total_amount")
        if not invoice.vendor or not invoice.vendor.gstin:
            missing.append("vendor_gstin")

        if not missing:
            return invoice

        prompt = f"""
Extract the following fields from the invoice text.

Fields: {missing}

Return STRICT JSON only.

Invoice text:
{text}
"""

        try:
            response = self.llm(prompt)
            data = self._safe_json(response)

            invoice.invoice_number = invoice.invoice_number or data.get("invoice_number")
            invoice.invoice_date = invoice.invoice_date or self._parse_date(
                data.get("invoice_date")
            )
            invoice.total_amount = invoice.total_amount or self._safe_float(
                data.get("total_amount")
            )

            if data.get("vendor_gstin"):
                if not invoice.vendor:
                    invoice.vendor = Vendor(gstin=data["vendor_gstin"])
                elif not invoice.vendor.gstin:
                    invoice.vendor.gstin = data["vendor_gstin"]

        except Exception as e:
            logger.warning(f"LLM assist failed: {e}")

        return invoice

     
    # HELPERS
     

    def _safe_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            return {}

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
            return int(str(v).replace(",", ""))
        except Exception:
            return None
