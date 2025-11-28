from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import requests
from dotenv import load_dotenv

load_dotenv()

VERYFI_CLIENT_ID = os.getenv("VERYFI_CLIENT_ID")
VERYFI_USERNAME = os.getenv("VERYFI_USERNAME")
VERYFI_API_KEY = os.getenv("VERYFI_API_KEY")
VERYFI_CLIENT_SECRET = os.getenv("VERYFI_CLIENT_SECRET")
VERYFI_SANDBOX = os.getenv("VERYFI_SANDBOX", "false").lower() == "true"

VERYFI_BASE_URL = "https://api.veryfi.com/api/v8"

app = FastAPI()


class BillItem(BaseModel):
    item_name: str
    item_amount: float
    item_rate: float
    item_quantity: float


class PageItems(BaseModel):
    page_no: str
    page_type: str  # "Bill Detail | Final Bill | Pharmacy"
    bill_items: List[BillItem]


class TokenUsage(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int


class DataOut(BaseModel):
    pagewise_line_items: List[PageItems]
    total_item_count: int
    reconciled_amount: float  # final total 


class ExtractResponse(BaseModel):
    is_success: bool
    token_usage: TokenUsage
    data: DataOut


class ExtractRequest(BaseModel):
    document: str


def call_veryfi_process_document_from_url(file_url: str) -> Dict[str, Any]:
    """
    Call Veryfi's Process Document endpoint with file_url.
    """
    if not (VERYFI_CLIENT_ID and VERYFI_USERNAME and VERYFI_API_KEY):
        raise HTTPException(status_code=500, detail="Veryfi credentials not configured")

    url = f"{VERYFI_BASE_URL}/partner/documents"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Client-Id": VERYFI_CLIENT_ID,
        "Authorization": f"apikey {VERYFI_USERNAME}:{VERYFI_API_KEY}",
    }

    payload = {
        "file_url": file_url,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
    except Exception:
        raise HTTPException(status_code=502, detail="Error calling Veryfi")

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Veryfi error: {resp.text}",
        )

    return resp.json()


def map_veryfi_to_our_schema(veryfi_doc: Dict[str, Any]) -> DataOut:
    line_items = veryfi_doc.get("line_items", []) or []

    bill_items: List[BillItem] = []
    for li in line_items:
        name = li.get("description") or ""
        amount = float(li.get("total", 0.0) or 0.0)
        rate = float(li.get("price", 0.0) or 0.0)
        qty = float(li.get("quantity", 0.0) or 0.0)

        bill_items.append(
            BillItem(
                item_name=name,
                item_amount=amount,
                item_rate=rate,
                item_quantity=qty,
            )
        )

    page = PageItems(
        page_no="1",
        page_type="Final Bill",
        bill_items=bill_items,
    )

    total_bill_amount = float(veryfi_doc.get("total", 0.0) or 0.0)

    return DataOut(
        pagewise_line_items=[page],
        total_item_count=len(bill_items),
        reconciled_amount=total_bill_amount,
    )


@app.post("/extract-bill-data", response_model=ExtractResponse)
async def extract_bill_data(req: ExtractRequest):
    """
    Submission endpoint.
    Input: { "document": "<DOCUMENT_URL>" }
    We pass document as file_url to Veryfi, then map their response to required schema.
    """
    file_url = req.document

    veryfi_doc = call_veryfi_process_document_from_url(file_url)

    data = map_veryfi_to_our_schema(veryfi_doc)

    token_usage = TokenUsage(total_tokens=0, input_tokens=0, output_tokens=0)

    return ExtractResponse(
        is_success=True,
        token_usage=token_usage,
        data=data,
    )
