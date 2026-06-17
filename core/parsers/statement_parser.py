"""
services/llm_parser.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Direct LLM transaction extraction from raw PDF text.

Uses call_llm() which tries Gemini direct â†’ Gemini via OpenRouter â†’
fallback model, so a single provider being overloaded never stalls the pipeline.

NOTE: parse_with_vision() removed â€” OCR path not included in minimal core.
"""

import re
import json
import logging

from config import LLM_PARSER_MODEL
from core.llm.provider import call_llm

logger = logging.getLogger("ledgerai.llm_parser")

_CHUNK_SIZE = 10


class TransactionExtractionFailure(Exception):
    def __init__(self, message, partial_result):
        super().__init__(message)
        self.partial_result = partial_result

def parse_with_llm(full_text: str, identifier_json: dict) -> str:
    """
    Split full_text into page chunks, extract transactions per chunk,
    merge all results and return as a JSON array string.
    """
    doc_family  = identifier_json.get("document_family", "BANK_ACCOUNT_STATEMENT")
    doc_subtype = identifier_json.get("document_subtype", "")
    institution = identifier_json.get("institution_name", "Unknown")

    pages = [
        block.strip()
        for block in re.split(r'={80}', full_text)
        if block.strip() and not re.fullmatch(r'\s*PAGE\s+\d+\s*', block.strip(), re.IGNORECASE)
    ]
    if not pages:
        pages = [full_text]

    total_pages = len(pages)
    
    from core.extractors.pdf_extractor import DATE_RE
    expected_transactions = False
    upper_text = full_text.upper()
    keywords = ["UPI", "IMPS", "NEFT", "RTGS", "ATM", "POS", "ACH", "NACH"]
    if any(kw in upper_text for kw in keywords):
        expected_transactions = True
    elif len(DATE_RE.findall(full_text)) > 5:
        expected_transactions = True
        
    logger.info(
        "LLM parse start: family=%s institution=%s pages=%d chunk_size=%d expected_txns=%s",
        doc_family, institution, total_pages, _CHUNK_SIZE, expected_transactions
    )

    all_txns = []
    combined_raw_response = []
    combined_prompts = []
    last_provider = "unknown"
    last_model = "unknown"

    for chunk_start in range(0, total_pages, _CHUNK_SIZE):
        chunk_pages = pages[chunk_start: chunk_start + _CHUNK_SIZE]
        chunk_end   = chunk_start + len(chunk_pages)
        chunk_text  = "\n\n".join(chunk_pages)

        logger.info(
            "LLM chunk pages %d–%d of %d (text_len=%d)",
            chunk_start + 1, chunk_end, total_pages, len(chunk_text),
        )

        try:
            llm_result = _parse_chunk(
                chunk_text=chunk_text,
                doc_family=doc_family,
                doc_subtype=doc_subtype,
                institution=institution,
            )
            raw_response = llm_result["raw_response"]
            chunk_txns = _safe_parse_json(raw_response, chunk_start + 1, chunk_end)

            if not chunk_txns and len(chunk_text.splitlines()) > 50:
                logger.warning("LLM returned [] but chunk has >50 lines. Retrying with strict directive.")
                retry_llm_result = _parse_chunk(
                    chunk_text=chunk_text,
                    doc_family=doc_family,
                    doc_subtype=doc_subtype,
                    institution=institution,
                    strict_retry=True
                )
                llm_result = retry_llm_result
                raw_response = llm_result["raw_response"]
                chunk_txns = _safe_parse_json(raw_response, chunk_start + 1, chunk_end)

            combined_raw_response.append(raw_response)
            combined_prompts.append(llm_result["prompt_text"])
            last_provider = llm_result["provider"]
            last_model = llm_result["model"]
            
            all_txns.extend(chunk_txns)
            logger.info(
                "LLM chunk pages %d–%d: extracted %d transactions (running total=%d)",
                chunk_start + 1, chunk_end, len(chunk_txns), len(all_txns),
            )
        except Exception as e:
            logger.error(
                "LLM chunk pages %d–%d FAILED: %s — skipping chunk",
                chunk_start + 1, chunk_end, e,
            )

    logger.info(
        "LLM parse complete: %d total transactions across %d pages",
        len(all_txns), total_pages,
    )

    result = {
        "raw_response": "\n\n---\n\n".join(combined_raw_response) if combined_raw_response else "[]",
        "prompt_text": "\n\n---\n\n".join(combined_prompts) if combined_prompts else "",
        "provider": last_provider,
        "model": last_model,
        "transactions": all_txns
    }

    if expected_transactions and len(all_txns) == 0:
        raise TransactionExtractionFailure("TRANSACTION_EXTRACTION_FAILURE: Expected transactions based on text heuristic, but LLM returned 0 transactions.", result)

    return result


# ————————————————————————————————————————————————————————————————————————————————————
# INTERNAL HELPERS
# ————————————————————————————————————————————————————————————————————————————————————

def _parse_chunk(
    chunk_text: str,
    doc_family: str,
    doc_subtype: str,
    institution: str,
    strict_retry: bool = False
) -> dict:
    strict_msg = "CRITICAL INSTRUCTION: Return every transaction row visible in the statement. Do not return [] unless absolutely no transactions exist. You MUST find transactions if they are present in the text below.\n\n" if strict_retry else ""
    prompt = f"""
You are a financial data extraction engine.

Extract ALL transaction entries from the provided document text.

{strict_msg}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
DOCUMENT INFO
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Document Family: {doc_family}
Document Subtype: {doc_subtype}
Institution: {institution}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
RULES
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

1. Extract EVERY transaction row. A transaction starts with a date.
2. SKIP these entirely â€” they are NOT transactions:
   - Headers (Date, Particulars, Debit, Credit, Balance)
   - Footers (Page numbers, disclaimers, generated on...)
   - Summary rows (Opening Balance, Closing Balance, Total Debit/Credit)
   - Account info (Branch, IFSC, MICR, Account Number)
3. MULTI-LINE NARRATION â€” CRITICAL:
   - Many bank statements split a single transaction's description across 2 or 3 lines.
   - A continuation line does NOT start with a date and does NOT contain an amount or balance.
   - You MUST append continuation lines to the PREVIOUS transaction's "narration" field using a single space.
   - NEVER create a separate transaction entry for a continuation line.
   - Example:
       Line 1: "01/04/2026  UPI/CR/123456/ACME    5000.00  95000.00"
       Line 2: "CORP PAYMENT APRIL"
     â†’ narration = "UPI/CR/123456/ACME CORP PAYMENT APRIL"  (one transaction, merged)
4. NARRATION field must contain ONLY the transaction narration/description:
   - Do NOT include dates, amounts, page numbers, or header text in narration.
   - Do NOT include footer text, branch info, or account numbers in narration.
   - Example GOOD: "NEFT CR ACME CORP SALARY"
   - Example BAD: "01/01/2025 NEFT CR ACME CORP 50000.00 Page 1 of 3"
5. Handle Indian number formats (1,00,000.00).
6. Normalize dates to YYYY-MM-DD.
7. DEBIT/CREDIT: Every transaction MUST have either debit or credit filled (not both None).
   - If running balance increases, the amount is credit.
   - If running balance decreases, the amount is debit.
   - If column headers say Withdrawal/Debit use those.
   - If column headers say Deposit/Credit use those.

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
OUTPUT FORMAT (JSON ARRAY)
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

[
  {{
    "date": "YYYY-MM-DD",
    "narration": "<transaction description only, no dates/amounts/noise>",
    "debit": <float or null>,
    "credit": <float or null>,
    "balance": <float or null>
  }}
]

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
DOCUMENT TEXT
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

{chunk_text}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Return ONLY the JSON array. No markdown. No explanation.
"""

    return call_llm(prompt=prompt, temperature=0)


def _safe_parse_json(response: str, page_from: int, page_to: int) -> list:
    cleaned = response.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "LLM chunk pages %dâ€“%d: JSON parse failed (%s). Preview: %s",
                page_from, page_to, e, cleaned[:300],
            )
            return []
    logger.warning(
        "LLM chunk pages %dâ€“%d: no JSON array found in response. Preview: %s",
        page_from, page_to, cleaned[:300],
    )
    return []

