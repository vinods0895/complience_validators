# tools/state_manager.py
class StateManager:
    def __init__(self):
        self.seen_invoices = set()
        self.vendor_totals = {}

    def check_duplicate(self, invoice_no: str) -> bool:
        if invoice_no in self.seen_invoices:
            return True
        self.seen_invoices.add(invoice_no)
        return False

    def track_vendor_total(self, vendor: str, amount: float):
        self.vendor_totals[vendor] = self.vendor_totals.get(vendor, 0) + amount
        return self.vendor_totals[vendor]
