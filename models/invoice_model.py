from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


# -------------------------------------------------
# Helper: flexible date parsing
# -------------------------------------------------

def parse_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


# -------------------------------------------------
# Line Item
# -------------------------------------------------

class LineItem(BaseModel):
    description: Optional[str] = None
    hsn_sac: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    rate: Optional[float] = None
    amount: Optional[float] = None

    cgst_rate: Optional[float] = None
    sgst_rate: Optional[float] = None
    igst_rate: Optional[float] = None

    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None


# -------------------------------------------------
# Vendor
# -------------------------------------------------

class Vendor(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None


# -------------------------------------------------
# Buyer
# -------------------------------------------------

class Buyer(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None


# -------------------------------------------------
# Invoice Model
# -------------------------------------------------

class InvoiceModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None

    vendor: Optional[Vendor] = None
    buyer: Optional[Buyer] = None

    line_items: List[LineItem] = Field(default_factory=list)

    subtotal: Optional[float] = None
    cgst_rate: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_rate: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_rate: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax: Optional[float] = None
    total_amount: Optional[float] = None

    currency: Optional[str] = None

    irn: Optional[str] = None
    irn_date: Optional[date] = None
    qr_code_present: Optional[bool] = None
    payment_terms: Optional[str] = None
    po_reference: Optional[str] = None
    notes: Optional[str] = None

    transport_mode: Optional[str] = None
    vehicle_number: Optional[str] = None
    eway_bill: Optional[str] = None

    # -----------------------------
    # Date validators
    # -----------------------------

    @field_validator("invoice_date", "irn_date", mode="before")
    @classmethod
    def validate_dates(cls, value):
        return parse_date(value)
