from typing import Dict, Tuple


class StateManager:
    """
    Regulatory state store.

    Stores only minimal facts required for
    cross-invoice compliance checks.
    """

    def __init__(self):
        # Vendor + Financial Year aggregates
        self.vendor_fy_totals: Dict[
            Tuple[str, str], Dict[str, float]
        ] = {}

        # Duplicate detection: (vendor_gstin, invoice_number)
        self.seen_invoices: set[Tuple[str, str]] = set()

        # Last invoice per vendor (for sequencing)
        self.last_invoice_by_vendor: Dict[str, Dict] = {}

    # DUPLICATE DETECTION

    def is_duplicate_invoice(
        self,
        vendor_gstin: str,
        invoice_number: str,
    ) -> bool:
        key = (vendor_gstin, invoice_number)

        if key in self.seen_invoices:
            return True

        self.seen_invoices.add(key)
        return False

    # VENDOR + FINANCIAL YEAR AGGREGATES

    def update_vendor_fy_totals(
        self,
        vendor_gstin: str,
        financial_year: str,
        invoice_amount: float,
        tds_amount: float = 0.0,
    ):
        key = (vendor_gstin, financial_year)

        record = self.vendor_fy_totals.setdefault(
            key,
            {
                "total_invoice_amount": 0.0,
                "total_tds_deducted": 0.0,
                "invoice_count": 0,
            },
        )

        record["total_invoice_amount"] += invoice_amount
        record["total_tds_deducted"] += tds_amount
        record["invoice_count"] += 1

    def get_vendor_fy_totals(
        self,
        vendor_gstin: str,
        financial_year: str,
    ) -> Dict[str, float]:
        return self.vendor_fy_totals.get(
            (vendor_gstin, financial_year),
            {
                "total_invoice_amount": 0.0,
                "total_tds_deducted": 0.0,
                "invoice_count": 0,
            },
        )

    # INVOICE SEQUENCE CHECK

    def check_invoice_sequence(
        self,
        vendor_gstin: str,
        invoice_number: str,
        invoice_date: str,
    ) -> Dict:
        prev = self.last_invoice_by_vendor.get(vendor_gstin)

        self.last_invoice_by_vendor[vendor_gstin] = {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
        }

        if not prev:
            return {"sequence_ok": True}

        if invoice_date < prev["invoice_date"]:
            return {
                "sequence_ok": False,
                "issue": "Invoice date older than previous invoice",
            }

        return {"sequence_ok": True}
