from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


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


class Vendor(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    address: Optional[str] = None


class Buyer(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None


class InvoiceModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"
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
