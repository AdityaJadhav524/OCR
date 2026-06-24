# TRANSACTION LOSS AUDIT

**Total Raw Rows:** 3367
**Total Candidate Rows:** 715
**Total Blocks:** 814
**Total Accepted:** 689

## Loss Breakdown
- **Balance/Amount Corruption:** 25
- **Over-aggressive Reject:** 19
- **Row Merge Collapse:** 5

## Top Missing Transactions
```json
{
  "pdf": "axis.pdf",
  "raw_row": "23-10-2021 NEFT/MBJAXMB212965736399Nishur Pathan 25000.00| 42882.00z8",
  "merged_into": "23-10-2021 NEFT/MBJAXMB212965736399Nishur Pathan 25000.00| 42882.00z8 | NEFT/MB/AXMB212965736646/Pathun Fardeen",
  "lost_at": "QUALIFIES",
  "reason": "NO_TRANSACTION_SEED"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "25-10-2021 Enterprisesok 299999.0g 785.00 78",
  "merged_into": "25-10-2021 Enterprisesok 299999.0g 785.00 78",
  "lost_at": "QUALIFIES",
  "reason": "no_debit_or_credit"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "28-10-2021 785.00| 128",
  "merged_into": "28-10-2021 785.00| 128 | |SAK NEFTRTGS Ckurgas caRa.l990000",
  "lost_at": "QUALIFIES",
  "reason": "no_debit_or_credit"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "30-10-2021 29.50 696.50 178",
  "merged_into": "30-10-2021 29.50 696.50 178 | DBak oi | CPP2AI3015690S654/NISHAR 1% | 3)-10-2021 10000.00 10696 | UPLP2NI30456913471/NISHAR IDBank of",
  "lost_at": "QUALIFIES",
  "reason": "both_debit_and_credit"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "12-11-2021 Enteriss 290000.00! 634.50 178",
  "merged_into": "12-11-2021 Enteriss 290000.00! 634.50 178",
  "lost_at": "QUALIFIES",
  "reason": "no_debit_or_credit"
}
```
```json
{
  "pdf": "axis.pdf",
  "raw_row": "18-11-202L f6z601547-RENTAL,NOV 2021CA I8-NOV-2t 21030 159.70 178",
  "merged_into": "12-1-2021 027/171121 251.00 37001 | 18-11-202L f6z601547-RENTAL,NOV 2021CA I8-NOV-2t 21030 159.70 178",
  "lost_at": "BLOCK_MERGE",
  "reason": "swallowed_by_merge"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "28/12/2024 COLLECTION-28/12/2024 126-148234845 000000 14,800.00 12,532.14CR",
  "merged_into": "28/12/2024 COLLECTION-28/12/2024 126-148234845 000000 14,800.00 12,532.14CR | UPI/DR/436549725664/Zerod | ha 126-148234847 000000 8,000.00 4,532.14CR",
  "lost_at": "QUALIFIES",
  "reason": "both_debit_and_credit"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "02/01/2025 PUROHIT 126-161170290 000000 90.00 13,083.07CR",
  "merged_into": "02/01/2025 PUROHIT 126-161170290 000000 90.00 13,083.07CR | FA/YESB/001425000000051/F | apada | UPI/DR/500338043991/Bajaj | Auto 126-161170299 000000 10,082.00 3,001.07CR",
  "lost_at": "QUALIFIES",
  "reason": "both_debit_and_credit"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "3005/25 UPI-SAI PARK 0000338148174038 30/05/25 280.00 693,543.42",
  "merged_into": "30/05/25 UPI-MR RANVUAY KUMAR 0000018785526161 30/05/25 70.00 693.823.42 | RANVJAYK262@OK | AXIS-CBIN0282444-018785526161-CLOTHES PR | ESS | 3005/25 UPI-SAI PARK 0000338148174038 30/05/25 280.00 693,543.42 | IN-PAYIMQRIFHYLH2FHT@PAYTM | YESB0PTMUPI-338148174038-THALI",
  "lost_at": "BLOCK_MERGE",
  "reason": "swallowed_by_merge"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "02/05/25 IB BILLPAYDR-HDFCEL-457704XXXXXX6080 MB02154346030T13 02/05/25 19.071.00 756.415.97",
  "merged_into": "02/05/25 IB BILLPAYDR-HDFCEL-457704XXXXXX6080 MB02154346030T13 02/05/25 19.071.00 756.415.97",
  "lost_at": "QUALIFIES",
  "reason": "NO_TRANSACTION_SEED"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "28/05/25UPI-YOGESHWARI-VYAPAR173204547941@HDFCB 0000961239764357 28/05/25 100.00 698.708.52",
  "merged_into": "27/05/25 UPI-SATYAVAN RAJU 000031872738584827/05/25 125.00 698,808.52 | SHIKHA-SHIKHARESATISH2 | 715@OKSBI-BKID0000503-318727385848-AUTO | 28/05/25UPI-YOGESHWARI-VYAPAR173204547941@HDFCB 0000961239764357 28/05/25 100.00 698.708.52 | ANK-HDFC0MERUPI-961239764357-POHE",
  "lost_at": "BLOCK_MERGE",
  "reason": "swallowed_by_merge"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "28/05/25 UPI-AVADHUT ASHOK 0000376095188543 28/05/25 1,810.00 699,490.42",
  "merged_into": "28/05/25 UPI-AVADHUT ASHOK 0000376095188543 28/05/25 1,810.00 699,490.42 | GHARGE-BAJARANG.GHARGE | @YBL-HDFC0000222-376095188543-AKLUJ TRIP | 2805/25 UPI-SWEEKARVEGRESTAURANI-PAYTMQRI6J3N248 0000418449608286 28/05/25 740.00 698,750.42 | XL@PAYTM-YESB0PTMUPI-418449508286-DINNER",
  "lost_at": "QUALIFIES",
  "reason": "both_debit_and_credit"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "2805/25 UPI-SWEEKARVEGRESTAURANI-PAYTMQRI6J3N248 0000418449608286 28/05/25 740.00 698,750.42",
  "merged_into": "28/05/25 UPI-AVADHUT ASHOK 0000376095188543 28/05/25 1,810.00 699,490.42 | GHARGE-BAJARANG.GHARGE | @YBL-HDFC0000222-376095188543-AKLUJ TRIP | 2805/25 UPI-SWEEKARVEGRESTAURANI-PAYTMQRI6J3N248 0000418449608286 28/05/25 740.00 698,750.42 | XL@PAYTM-YESB0PTMUPI-418449508286-DINNER",
  "lost_at": "QUALIFIES",
  "reason": "both_debit_and_credit"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "3005/25 UPI-SHIVAMFOR 0000679057859474 30/05/25 1,499.00 695,053.42",
  "merged_into": "30/05/25 UPI-VIKRAM 0000330722090216 30/05/25 190.00 696,552.42 | CATERERS-BHARATPE90727958943@ | YESBANKLTD-YESB0YESUPI-330722090216-PAY | TO BHARATPE ME | 3005/25 UPI-SHIVAMFOR 0000679057859474 30/05/25 1,499.00 695,053.42 | MEN-PAYTMQR6SOQME@PTYS-YE | SB0PTMUPI-679057859474-JACKET",
  "lost_at": "BLOCK_MERGE",
  "reason": "swallowed_by_merge"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "06/05/25 UPI-MASTER SOURABH 0000855742328652 06/05/25 $7.00 760,477.97",
  "merged_into": "06/05/25 UPI-MASTER SOURABH 0000855742328652 06/05/25 $7.00 760,477.97 | SUNIL-PAYTMQRIATOFYMQ | HDFC BANK LIMITED | t is that ou secord with the Bank as at the day of requesting",
  "lost_at": "QUALIFIES",
  "reason": "no_debit_or_credit"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "Available Balance \u20b977,051.12 CR Ledger Balance \u20b977,051.12 CR",
  "merged_into": "From Date 01/10/2024 To Date 31/03/2025 | Account Details | Account Number 087110100001357 Account Currency INR (\u20b9) | Account Name UMESH VILAS PATIL Branch SANGLI BRANCH | Available Balance \u20b977,051.12 CR Ledger Balance \u20b977,051.12 CR | Hold Amount \u20b90.00 Accrued Interest \u20b974.45 | Joint Holder N/A Opening Balance -\u20b91,53,008.95 | Transaction Date Description Txn Reference/Instrument Cheque No Debit Amount(\u20b9) Credit Amount(\u20b9) Running Balance | UPI/CR/427669681424/UMES | H VILAS",
  "lost_at": "QUALIFIES",
  "reason": "no_date"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "Hold Amount \u20b90.00 Accrued Interest \u20b974.45",
  "merged_into": "From Date 01/10/2024 To Date 31/03/2025 | Account Details | Account Number 087110100001357 Account Currency INR (\u20b9) | Account Name UMESH VILAS PATIL Branch SANGLI BRANCH | Available Balance \u20b977,051.12 CR Ledger Balance \u20b977,051.12 CR | Hold Amount \u20b90.00 Accrued Interest \u20b974.45 | Joint Holder N/A Opening Balance -\u20b91,53,008.95 | Transaction Date Description Txn Reference/Instrument Cheque No Debit Amount(\u20b9) Credit Amount(\u20b9) Running Balance | UPI/CR/427669681424/UMES | H VILAS",
  "lost_at": "QUALIFIES",
  "reason": "no_date"
}
```
```json
{
  "pdf": "24-25 -2 2.pdf",
  "raw_row": "259 44 215 \u20b99,14,124.74 \u20b911,44,184.81",
  "merged_into": "31-03-2025 55-549515 000000 143.00 2,40,284.86 CR | 31032025 | Transaction Summary | Total Transactions Number of Credits Number of Debits Debit Amount Credit Amount | 259 44 215 \u20b99,14,124.74 \u20b911,44,184.81 | System generated receipt doesn\u2019t require signature",
  "lost_at": "BLOCK_MERGE",
  "reason": "swallowed_by_merge"
}
```
```json
{
  "pdf": "YESBANK_SAVINGS_DIGITAL.pdf",
  "raw_row": "16/11/21 ATW-416021XXXXX8811-P1DCHS03- JALANDHAR 0000000000009009 16/07/21 10.000.00 288,110.60",
  "merged_into": "16/11/21 ATW-416021XXXXX8811-P1DCHS03- JALANDHAR 0000000000009009 16/07/21 10.000.00 288,110.60",
  "lost_at": "QUALIFIES",
  "reason": "no_debit_or_credit"
}
```
```json
{
  "pdf": "YESBANK_SAVINGS_DIGITAL.pdf",
  "raw_row": "14/12/21 NWD-416021XXXXXX8811-92454003-PUNJAB 0000122610065793 14/08/21 10.000.00 203.020.73",
  "merged_into": "14/12/21 NWD-416021XXXXXX8811-92454003-PUNJAB 0000122610065793 14/08/21 10.000.00 203.020.73",
  "lost_at": "QUALIFIES",
  "reason": "NO_TRANSACTION_SEED"
}
```

## Top Corrupted Transactions
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "29/11/2024 KRUSHNAT/FDRL/138202000 126-148234839 000000 80.00",
  "merged_into": "29/11/2024 KRUSHNAT/FDRL/138202000 126-148234839 000000 80.00 | 70130/Pay to Bh | UPI/DR/684917996675/ROHI | T BABURAO",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "04/12/2024 P/FDRL/13820200070130/Bre 126-148234763 000000 80.00",
  "merged_into": "04/12/2024 P/FDRL/13820200070130/Bre 126-148234763 000000 80.00 | akfast | UPI/DR/475508959859/SHUB",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "15/02/2025 SHEVAD/BKID0000515/rajkish 42-7644569 000000 150.00",
  "merged_into": "15/02/2025 SHEVAD/BKID0000515/rajkish 42-7644569 000000 150.00 | an94645-2@oksbi/Bangles | UPI/DR/602309062013/BALIS | HTAR 000000",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "29-03-2025 C0000001/HDFCH001488346 000000 5,00,000.00",
  "merged_into": "29-03-2025 C0000001/HDFCH001488346 000000 5,00,000.00 | 73 | IBNEFT/TJSBH25088157127/ | WJVILAS TECHNOLOGIES &",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "09/12/2024 BACHCHA/YESB/0014250000 126-148234792 000000 40.00",
  "merged_into": "09/12/2024 BACHCHA/YESB/0014250000 126-148234792 000000 40.00 | 00051/Nastha | UPI/DR/630987859659/KUMA",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "16/01/2025 COM/HDFC/50200027864076/ 000000 149.00",
  "merged_into": "16/01/2025 COM/HDFC/50200027864076/ 000000 149.00 | Monthly autop | UPI/DR/471191592919/Sun",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "20/01/2025 TEKCHAND/YESB/001425000 126-161169899 000000 38.00",
  "merged_into": "20/01/2025 TEKCHAND/YESB/001425000 126-161169899 000000 38.00 | 000051/Medicine | UPI/DR/271003588581/BHAR | AT",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "26-12-2024 ENTERP/HDFC/502000945634 126-148234828 000000 16,000.00",
  "merged_into": "26-12-2024 ENTERP/HDFC/502000945634 126-148234828 000000 16,000.00 | 35/car inst | 2758944108B0I EMI",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "raw_row": "20/11/2024 G/YESB/002261100000025/M 126-148234393 000000 48.00",
  "merged_into": "20/11/2024 G/YESB/002261100000025/M 126-148234393 000000 48.00 | edicine | UPI/DR/741102155880/UJJVI",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "17/05/25 UPI-RUPALI MAHADEV 0000432605954878 17/05/25 30.00 728.662.39",
  "merged_into": "17/05/25 UPI-RUPALI MAHADEV 0000432605954878 17/05/25 30.00 728.662.39 | HDFC BANK LIMITED",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "30/05/25 UPI-MR LALIT KUMAR PUK-Q754238133@YBL 0000052855723886 30/05/25 100.00 693.443.42",
  "merged_into": "30/05/25 UPI-MR LALIT KUMAR PUK-Q754238133@YBL 0000052855723886 30/05/25 100.00 693.443.42 | YESB0YBLUPI-052855723886-CHOCOLATE",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "31/05/25 UPI-RUPALI MAHADEV 0000282893215661 31/05/25 30.00 691.773.70",
  "merged_into": "31/05/25 UPI-RUPALI MAHADEV 0000282893215661 31/05/25 30.00 691.773.70 | SWAMI-GPAY-1120902103 | 2@OKBIZAXIS-UT1B0000553-282898215661-PAY | MENT FROM PHONE",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "03/05/25 UPI-PMBANATWALA-STK-9665971874-1@OKBIZ 0000964203916371 03/05/25 48.00 776.184.97",
  "merged_into": "03/05/25 UPI-PMBANATWALA-STK-9665971874-1@OKBIZ 0000964203916371 03/05/25 48.00 776.184.97 | AXIS-UTIB0000553-964208916371-LIFAFE",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "29/05/25 UPI-VRAJU 0000022264194605 29/05/25 25.00 697.729.42",
  "merged_into": "29/05/25 UPI-VRAJU 0000022264194605 29/05/25 25.00 697.729.42 | HDFC BANK LIMITED",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "30/05/25 UPI-MR NEHERUL ALAM.Q900083679YBL-YES 0000820382615256 30/05/25 30.00 695.023.42",
  "merged_into": "30/05/25 UPI-MR NEHERUL ALAM.Q900083679YBL-YES 0000820382615256 30/05/25 30.00 695.023.42 | BOYBLUPI-820382615256-POLISH",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "05/05/25 UPI-UJJVILAS ENTERPRISES-8999416530-2@IB 0000987357529597 05/05/25 7,080.00 760.689.97",
  "merged_into": "05/05/25 UPI-UJJVILAS ENTERPRISES-8999416530-2@IB 0000987357529597 05/05/25 7,080.00 760.689.97 | L-HDFC0000222-987357529597-FOR SSL",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "09/05/25 UPI-HARMAN CHAHAWALA 0000385121128725 09/05/25 75.00 754.885.39",
  "merged_into": "09/05/25 UPI-HARMAN CHAHAWALA 0000385121128725 09/05/25 75.00 754.885.39 | COL-GPAY-1125157392 | 9@OKBIZAXIS-UIIB0000553-385121128725-NAS | THA",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "10/05/25 UPI-SAGAR GOPALRAO 0000182964059648 10/05/25 350.00 753.867.39",
  "merged_into": "10/05/25 UPI-SAGAR GOPALRAO 0000182964059648 10/05/25 350.00 753.867.39 | PATIL-PAYIMQR6BMASD@P | TYS-YESB0PTMUPI-182964059648-ICECREAM",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "18/05/25 UPI-ROHAN SHASHIKANT 0000044449440210 18/05/25 14,640.00 714.022.39",
  "merged_into": "18/05/25 UPI-ROHAN SHASHIKANT 0000044449440210 18/05/25 14,640.00 714.022.39 | PAT-ROHAN.PATIL49@Y | BL-HDFC0000437-044449440210-MATTRESS",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```
```json
{
  "pdf": "HDFC_SAVINGS_SCANNED.pdf",
  "raw_row": "22/05/25 UPI-POCKIT TECHNOLOGIES 0000514222815960 22/05/25 1.00 701.159.52",
  "merged_into": "22/05/25 UPI-POCKIT TECHNOLOGIES 0000514222815960 22/05/25 1.00 701.159.52 | HDFC BANK LIMITED",
  "lost_at": "QUALIFIES",
  "reason": "missing_balance"
}
```

## Reject Reason Heatmap
### Global Ranking
- **missing_balance**: 25
- **both_debit_and_credit**: 7
- **no_debit_or_credit**: 6
- **swallowed_by_merge**: 5
- **NO_TRANSACTION_SEED**: 4
- **no_date**: 2

### By PDF
#### 24-25 -2 2.pdf
- **no_date**: 2
- **swallowed_by_merge**: 1
#### BOI_SAVINGS_SCANNED.pdf
- **missing_balance**: 9
- **both_debit_and_credit**: 2
#### HDFC_SAVINGS_SCANNED.pdf
- **missing_balance**: 11
- **swallowed_by_merge**: 3
- **both_debit_and_credit**: 2
- **NO_TRANSACTION_SEED**: 1
- **no_debit_or_credit**: 1
#### YESBANK_SAVINGS_DIGITAL.pdf
- **missing_balance**: 5
- **no_debit_or_credit**: 2
- **NO_TRANSACTION_SEED**: 2
- **both_debit_and_credit**: 2
#### axis.pdf
- **no_debit_or_credit**: 3
- **NO_TRANSACTION_SEED**: 1
- **both_debit_and_credit**: 1
- **swallowed_by_merge**: 1