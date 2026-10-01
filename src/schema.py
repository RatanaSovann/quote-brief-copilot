"""The job card shape. The LLM must return exactly this, and pydantic checks it did."""
from typing import Literal, Optional, Union

from pydantic import BaseModel

Status = Literal["stated", "inferred", "missing", "conflict"]


class JobField(BaseModel):
    # bool is allowed because install_required is a yes/no, not free text.
    value: Optional[Union[str, bool]]
    status: Status
    evidence: Optional[str]


class JobCard(BaseModel):
    # Every field is always present, so "not mentioned" is an explicit
    # status=missing rather than a silently absent key.
    customer_name: JobField
    contact: JobField
    suburb: JobField
    product_type: JobField
    other_products: JobField   # anything else they asked about; one card covers one product
    timeframe: JobField
    dimensions: JobField
    material_or_finish: JobField
    colour: JobField
    quantity: JobField
    install_required: JobField
    site_access: JobField
    budget_mentioned: JobField
    attachments_referenced: JobField
    notes: JobField


class Classification(BaseModel):
    """Step 1 output (Haiku). The label decides the route; the reason is for the run log."""
    label: Literal["enquiry", "complaint", "not_enquiry"]
    reason: str


class ReplyDraft(BaseModel):
    # Structured, not free text, so the model can't wrap the reply in
    # "Here's a draft:" chatter. Code adds the sign-off, not the model.
    body: str
