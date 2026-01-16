from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------
# Invoice Details
# -------------------------------------------------
class InvoiceDetails(BaseModel):
    invoice_id: Optional[str] = Field(
        default=None, description="Unique identifier for the invoice"
    )
    invoice_no: Optional[str] = Field(
        default=None, description="Invoice number"
    )
    invoice_date: Optional[str] = Field(
        default=None, description="Invoice date"
    )
    due_date: Optional[str] = None

    # ✅ Allow negative totals (credit notes / adjustments)
    total_amount: Optional[float] = Field(
        default=None, description="Invoice total (can be negative for credit notes)"
    )

    currency: Optional[str] = "INR"


# -------------------------------------------------
# Vendor Details
# -------------------------------------------------
class VendorDetails(BaseModel):
    vendor_id: Optional[str] = None
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    state_code: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    vendor_type: Optional[str] = None
    tds_section: Optional[str] = None
    registration_date: Optional[str] = None
    status: Optional[str] = None
    turnover_last_fy: Optional[float] = None
    gst_filing_status: Optional[str] = None
    lower_deduction_cert: Optional[str] = None
    msme_registered: Optional[bool] = None
    msme_category: Optional[str] = None


# -------------------------------------------------
# Customer Details
# -------------------------------------------------
class CustomerDetails(BaseModel):
    customer_name: Optional[str] = None
    gstin: Optional[str] = None


# -------------------------------------------------
# GST Details
# -------------------------------------------------
class GSTDetails(BaseModel):
    # ✅ Allow negative taxable value for credit notes
    taxable_value: Optional[float] = Field(
        None, description="Taxable value (can be negative for credit notes)"
    )

    cgst: Optional[float] = Field(
        None, description="CGST amount"
    )
    sgst: Optional[float] = Field(
        None, description="SGST amount"
    )
    igst: Optional[float] = Field(
        None, description="IGST amount"
    )


# -------------------------------------------------
# Line Item
# -------------------------------------------------
class LineItem(BaseModel):
    description: Optional[str] = None
    hsn: Optional[str] = None

    # Quantity & rate should not be negative
    quantity: Optional[float] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)

    cgst_rate: Optional[float] = Field(None, ge=0)
    sgst_rate: Optional[float] = Field(None, ge=0)
    igst_rate: Optional[float] = Field(None, ge=0)

    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None

    # ✅ Allow negative line amount (credit notes / discounts)
    amount: Optional[float] = Field(
        None, description="Line amount (can be negative)"
    )

    special_conditions: Optional[str] = None
    tds_section: Optional[str] = None


# -------------------------------------------------
# Root Invoice Model
# -------------------------------------------------
class InvoiceModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invoice_details: InvoiceDetails = Field(
        default_factory=InvoiceDetails
    )
    vendor_details: VendorDetails = Field(
        default_factory=VendorDetails
    )
    customer_details: CustomerDetails = Field(
        default_factory=CustomerDetails
    )

    gst_details: GSTDetails = Field(
        default_factory=lambda: GSTDetails(
            taxable_value=0,
            cgst=0,
            sgst=0,
            igst=0,
        )
    )

    line_items: List[LineItem] = Field(default_factory=list)
