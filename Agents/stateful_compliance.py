from typing import Dict, Any
from tools.state_manager import StateManager


class StatefulComplianceEngine:
    """
    Runs state-based compliance checks using StateManager.

    Emits compliance signals only.
    Does NOT make final decisions.
    """

    def __init__(
        self,
        state_manager: StateManager,
        tds_threshold: float = 1000000.0,
    ):
        self.state = state_manager
        self.tds_threshold = tds_threshold

    # CORE ENTRY POINT

    def run(
        self,
        invoice: Dict[str, Any],
        financial_year: str,
    ) -> Dict[str, Any]:

        vendor = (invoice.get("vendor") or {}).get("gstin")
        invoice_no = invoice.get("invoice_number")
        invoice_date = invoice.get("invoice_date")
        amount = invoice.get("total_amount") or 0.0
        tds_amount = invoice.get("tds_amount") or 0.0

        flags = {}
        evidence = {}

        # DUPLICATE CHECK
        if vendor and invoice_no:
            flags["duplicate_invoice"] = self.state.is_duplicate_invoice(
                vendor, invoice_no
            )
        else:
            flags["duplicate_invoice"] = False

        # INVOICE SEQUENCE CHECK
        if vendor and invoice_no and invoice_date:
            seq = self.state.check_invoice_sequence(
                vendor, invoice_no, invoice_date
            )
            flags["sequence_issue"] = not seq.get("sequence_ok", True)
        else:
            flags["sequence_issue"] = False

        # VENDOR FY AGGREGATE CHECK
        if vendor and financial_year:
            self.state.update_vendor_fy_totals(
                vendor_gstin=vendor,
                financial_year=financial_year,
                invoice_amount=amount,
                tds_amount=tds_amount,
            )

            totals = self.state.get_vendor_fy_totals(
                vendor, financial_year
            )

            evidence["vendor_fy_total"] = totals.get(
                "total_invoice_amount", 0.0
            )
            evidence["tds_threshold"] = self.tds_threshold

            flags["tds_threshold_crossed"] = (
                totals.get("total_invoice_amount", 0.0)
                > self.tds_threshold
            )
        else:
            flags["tds_threshold_crossed"] = False

        return {
            "stateful_flags": flags,
            "evidence": evidence,
        }
