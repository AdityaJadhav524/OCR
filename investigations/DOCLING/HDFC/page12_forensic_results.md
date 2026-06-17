# Docling Page 12 Forensic Evaluation Results

**Status:** 🔴 **FAIL**

Per the decision gate criteria, the Docling evaluation on the known-failing Page 12 (containing the POCKIT leak) has FAILED.

## Evidence

1. **Table detected:** Yes (1 table block).
2. **Footer outside table:** Yes (the footer text was successfully kept out of the Markdown table structure).
3. **Header detected:** Yes (Docling found 2 `section_header` blocks).
4. **Footer detected:** **NO.** 

Docling classified the entire footer region as generic `text` and `section_header`. 
It returned exactly **0** blocks of type `page_footer`.

### Extraction Excerpt (from `page12_layout.json`):

```json
  {
    "type": "section_header",
    "text": "HDFCBANKLIMITED",
    "bbox": [26.2, 81.0, 117.4, 72.5]
  },
  {
    "type": "text",
    "text": "Contensofisstatmenwillconsideredcectferiserdwihin30daysfecipftamenTeadrenhstamentshatnecordwithheBankasathedayfqesting this statement.",
    "bbox": [24.5, 65.3, 554.8, 47.5]
  },
  {
    "type": "text",
    "text": "*Closingbalanceincludesfundsearmarkedforhold andunclearedfunds",
    "bbox": [25.3, 73.4, 245.9, 63.2]
  },
  {
    "type": "text",
    "text": "RegisteredOffceAddress:HDFCBankHouse,SenapatiBapatMarg,LowerParel,Mumbai400013",
    "bbox": [25.3, 36.4, 286.9, 28.0]
  }
```

## Conclusion

Docling falls into the exact FAIL condition defined in the investigation prompt:
**"Footer classified as generic text"**

Because Docling classifies these blocks as generic text rather than `footer` elements, we would still have no programmatic way to distinguish them from valid transaction overflow text without applying the same exact-match suppression that is already failing on the PaddleOCR output.

Changing to Docling does not provide the semantic region classification needed to solve the `detect_transaction_blocks()` contamination issue. 

**Next Steps:**
Following the priority order, the full 12-page Docling benchmark has been **aborted**. 

I will now wait for your instructions on whether we should proceed to evaluate MinerU's layout separation capabilities, or if we should focus strictly on fixing the admission control bug inside our current `detect_transaction_blocks()` logic.
