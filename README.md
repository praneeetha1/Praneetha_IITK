# Bajaj HackRx Datathon – Invoice Data Extraction API

## This is my solution for the BFHL Datathon.
It’s a simple FastAPI service that takes a document URL, runs it through Veryfi OCR, and returns the extracted line items in the exact JSON format required for evaluation.

How it works (short architecture)
Document URL
    ↓
Veryfi OCR (line_items)
    ↓
Mapping layer → Cleaned items
    ↓
Page-type inference (simple rule)
    ↓
Final JSON response


## Design Choices

Used Veryfi because it handles messy/handwritten invoices well and already gives structured line-items.

No LLM → cheaper, faster, and predictable.

Page type is inferred with a small rule (pharma-related vendor name → “Pharmacy”, otherwise “Bill Detail”).

Output strictly follows the required Postman schema.

## Deployed Endpoint

POST https://bajaj-datathon-dugd.onrender.com/extract-bill-data