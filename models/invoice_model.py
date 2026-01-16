from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None


class InvoiceModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"
    )

    invoice_id: Optional[str] = None

    # 👇 KEY FIX
    invoice_no: Optional[str] = Field(
        default=None,
        alias="invoice_number"
    )

    invoice_date: Optional[str] = None

    vendor_gstin: Optional[str] = Field(
        default=None,
        alias="vendor.gstin"
    )

    buyer_gstin: Optional[str] = Field(
        default=None,
        alias="buyer.gstin"
    )

    items: List[LineItem] = Field(
        default_factory=list,
        alias="line_items"
    )

    total: Optional[float] = Field(
        default=None,
        alias="total_amount"
    )
