# FINAL 18 MISSING TRANSACTIONS REPORT

**Total Lost Transactions Identified:** 16

## Global Counts
- **ROW_MERGE_COLLAPSE**: 12
- **PAGE_BOUNDARY_COLLAPSE**: 0
- **MULTILINE_NARRATION_COLLAPSE**: 3
- **TRUE_OCR_FAILURE**: 1
- **POLICY_REJECT**: 0

## Per-PDF Breakdown
- **HDFC_SAVINGS_SCANNED.pdf**: 5 missing
- **24-25 -2 2.pdf**: 4 missing
- **axis.pdf**: 3 missing
- **BOI_SAVINGS_SCANNED.pdf**: 2 missing
- **YESBANK_SAVINGS_DIGITAL.pdf**: 2 missing

## Complete Forensic Traces
```json
{
  "pdf": "axis.pdf",
  "raw_row": "28-10-2021 785.00| 128",
  "merged_block": "28-10-2021 785.00| 128 | |SAK NEFTRTGS Ckurgas caRa.l990000",
  "candidate_score": 9,
  "reject_reason": "no_debit_or_credit",
  "date_detected": true,
  "amount_detected": false,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "TRUE_OCR_FAILURE"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "30-10-2021 29.50 696.50 178",
  "merged_block": "30-10-2021 29.50 696.50 178 | DBak oi | CPP2AI3015690S654/NISHAR 1% | 3)-10-2021 10000.00 10696 | UPLP2NI30456913471/NISHAR IDBank of",
  "candidate_score": 13,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "MULTILINE_NARRATION_COLLAPSE"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "18-11-202L f6z601547-RENTAL,NOV 2021CA I8-NOV-2t 21030 159.70 178",
  "merged_block": "12-1-2021 027/171121 251.00 37001 | 18-11-202L f6z601547-RENTAL,NOV 2021CA I8-NOV-2t 21030 159.70 178",
  "candidate_score": 9,
  "reject_reason": "swallowed_by_accepted_candidate",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "detect_transaction_blocks",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "28/12/2024 COLLECTION-28/12/2024 126-148234845 000000 14,800.00 12,532.14CR",
  "merged_block": "28/12/2024 COLLECTION-28/12/2024 126-148234845 000000 14,800.00 12,532.14CR | UPI/DR/436549725664/Zerod | ha 126-148234847 000000 8,000.00 4,532.14CR",
  "candidate_score": 11,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "MULTILINE_NARRATION_COLLAPSE"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "02/01/2025 PUROHIT 126-161170290 000000 90.00 13,083.07CR",
  "merged_block": "02/01/2025 PUROHIT 126-161170290 000000 90.00 13,083.07CR | FA/YESB/001425000000051/F | apada | UPI/DR/500338043991/Bajaj | Auto 126-161170299 000000 10,082.00 3,001.07CR",
  "candidate_score": 9,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "MULTILINE_NARRATION_COLLAPSE"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "3005/25 UPI-SAI PARK 0000338148174038 30/05/25 280.00 693,543.42",
  "merged_block": "30/05/25 UPI-MR RANVUAY KUMAR 0000018785526161 30/05/25 70.00 693.823.42 | RANVJAYK262@OK | AXIS-CBIN0282444-018785526161-CLOTHES PR | ESS | 3005/25 UPI-SAI PARK 0000338148174038 30/05/25 280.00 693,543.42 | IN-PAYIMQRIFHYLH2FHT@PAYTM | YESB0PTMUPI-338148174038-THALI",
  "candidate_score": 13,
  "reject_reason": "swallowed_by_accepted_candidate",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "detect_transaction_blocks",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "28/05/25UPI-YOGESHWARI-VYAPAR173204547941@HDFCB 0000961239764357 28/05/25 100.00 698.708.52",
  "merged_block": "27/05/25 UPI-SATYAVAN RAJU 000031872738584827/05/25 125.00 698,808.52 | SHIKHA-SHIKHARESATISH2 | 715@OKSBI-BKID0000503-318727385848-AUTO | 28/05/25UPI-YOGESHWARI-VYAPAR173204547941@HDFCB 0000961239764357 28/05/25 100.00 698.708.52 | ANK-HDFC0MERUPI-961239764357-POHE",
  "candidate_score": 15,
  "reject_reason": "swallowed_by_accepted_candidate",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "detect_transaction_blocks",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "28/05/25 UPI-AVADHUT ASHOK 0000376095188543 28/05/25 1,810.00 699,490.42",
  "merged_block": "28/05/25 UPI-AVADHUT ASHOK 0000376095188543 28/05/25 1,810.00 699,490.42 | GHARGE-BAJARANG.GHARGE | @YBL-HDFC0000222-376095188543-AKLUJ TRIP | 2805/25 UPI-SWEEKARVEGRESTAURANI-PAYTMQRI6J3N248 0000418449608286 28/05/25 740.00 698,750.42 | XL@PAYTM-YESB0PTMUPI-418449508286-DINNER",
  "candidate_score": 18,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "2805/25 UPI-SWEEKARVEGRESTAURANI-PAYTMQRI6J3N248 0000418449608286 28/05/25 740.00 698,750.42",
  "merged_block": "28/05/25 UPI-AVADHUT ASHOK 0000376095188543 28/05/25 1,810.00 699,490.42 | GHARGE-BAJARANG.GHARGE | @YBL-HDFC0000222-376095188543-AKLUJ TRIP | 2805/25 UPI-SWEEKARVEGRESTAURANI-PAYTMQRI6J3N248 0000418449608286 28/05/25 740.00 698,750.42 | XL@PAYTM-YESB0PTMUPI-418449508286-DINNER",
  "candidate_score": 13,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "3005/25 UPI-SHIVAMFOR 0000679057859474 30/05/25 1,499.00 695,053.42",
  "merged_block": "30/05/25 UPI-VIKRAM 0000330722090216 30/05/25 190.00 696,552.42 | CATERERS-BHARATPE90727958943@ | YESBANKLTD-YESB0YESUPI-330722090216-PAY | TO BHARATPE ME | 3005/25 UPI-SHIVAMFOR 0000679057859474 30/05/25 1,499.00 695,053.42 | MEN-PAYTMQR6SOQME@PTYS-YE | SB0PTMUPI-679057859474-JACKET",
  "candidate_score": 13,
  "reject_reason": "swallowed_by_accepted_candidate",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "detect_transaction_blocks",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "Available Balance \u20b977,051.12 CR Ledger Balance \u20b977,051.12 CR",
  "merged_block": "From Date 01/10/2024 To Date 31/03/2025 | Account Details | Account Number 087110100001357 Account Currency INR (\u20b9) | Account Name UMESH VILAS PATIL Branch SANGLI BRANCH | Available Balance \u20b977,051.12 CR Ledger Balance \u20b977,051.12 CR | Hold Amount \u20b90.00 Accrued Interest \u20b974.45 | Joint Holder N/A Opening Balance -\u20b91,53,008.95 | Transaction Date Description Txn Reference/Instrument Cheque No Debit Amount(\u20b9) Credit Amount(\u20b9) Running Balance | UPI/CR/427669681424/UMES | H VILAS",
  "candidate_score": 8,
  "reject_reason": "no_date",
  "date_detected": false,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "Hold Amount \u20b90.00 Accrued Interest \u20b974.45",
  "merged_block": "From Date 01/10/2024 To Date 31/03/2025 | Account Details | Account Number 087110100001357 Account Currency INR (\u20b9) | Account Name UMESH VILAS PATIL Branch SANGLI BRANCH | Available Balance \u20b977,051.12 CR Ledger Balance \u20b977,051.12 CR | Hold Amount \u20b90.00 Accrued Interest \u20b974.45 | Joint Holder N/A Opening Balance -\u20b91,53,008.95 | Transaction Date Description Txn Reference/Instrument Cheque No Debit Amount(\u20b9) Credit Amount(\u20b9) Running Balance | UPI/CR/427669681424/UMES | H VILAS",
  "candidate_score": 8,
  "reject_reason": "no_date",
  "date_detected": false,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "31-03-2025 55-549515 000000 143.00 2,40,284.86 CR",
  "merged_block": "31-03-2025 55-549515 000000 143.00 2,40,284.86 CR | 31032025 | Transaction Summary | Total Transactions Number of Credits Number of Debits Debit Amount Credit Amount | 259 44 215 \u20b99,14,124.74 \u20b911,44,184.81 | System generated receipt doesn\u2019t require signature",
  "candidate_score": 13,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "259 44 215 \u20b99,14,124.74 \u20b911,44,184.81",
  "merged_block": "31-03-2025 55-549515 000000 143.00 2,40,284.86 CR | 31032025 | Transaction Summary | Total Transactions Number of Credits Number of Debits Debit Amount Credit Amount | 259 44 215 \u20b99,14,124.74 \u20b911,44,184.81 | System generated receipt doesn\u2019t require signature",
  "candidate_score": 8,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "YESBANK_SAVINGS_DIGITAL.pdf",
  "raw_row": "07/02/22 ATW-416021XXXXXX8811-S1ANPZ50- 000000000000681708/10/21 5,000.00 464,850.50",
  "merged_block": "07/02/22 ATW-416021XXXXXX8811-S1ANPZ50- 000000000000681708/10/21 5,000.00 464,850.50 | HOSHIARPUR | 07/02/22UPI-HARPREET SINGH- 000012860877458713/10/21 25,000.00 489,850.50 | 07HARMANHAR@OKSBI-SB | IN0016901-128608774587-UPI",
  "candidate_score": 15,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```
```json
{
  "pdf": "YESBANK_SAVINGS_DIGITAL.pdf",
  "raw_row": "07/02/22UPI-HARPREET SINGH- 000012860877458713/10/21 25,000.00 489,850.50",
  "merged_block": "07/02/22 ATW-416021XXXXXX8811-S1ANPZ50- 000000000000681708/10/21 5,000.00 464,850.50 | HOSHIARPUR | 07/02/22UPI-HARPREET SINGH- 000012860877458713/10/21 25,000.00 489,850.50 | 07HARMANHAR@OKSBI-SB | IN0016901-128608774587-UPI",
  "candidate_score": 15,
  "reject_reason": "both_debit_and_credit",
  "date_detected": true,
  "amount_detected": true,
  "balance_detected": true,
  "lost_stage": "_qualifies",
  "category": "ROW_MERGE_COLLAPSE"
}
```

## Engineering Recommendation
*(Auto-generated based on highest classifications)*

**Primary Remaining Defect**: ROW_MERGE_COLLAPSE

**Recommendation**: Fixing row merge logic is HIGH RISK. Row merge keeps multiline narrations together. Tuning it to split merged rows might fracture hundreds of valid transactions. Given this affects extremely few rows, it is likely NOT worth the engineering effort to redesign `detect_transaction_blocks`.