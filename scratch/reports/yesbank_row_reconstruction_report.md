# YES Bank Scanned Row Reconstruction Forensic Report

## 1. OCR Row Classification Summary

Total OCR rows:         227
Total tokens:           739
Pages:                  4

| Row Type | Count | Meaning |
|----------|-------|---------|
| TXN_ANCHOR | 82 | Has date + balance → parser sees as transaction row |
| DATE_ONLY | 0 | Has date but no balance → date/amount split |
| AMOUNT_ORPHAN | 1 | Has amount + balance but no date → split from anchor |
| AMOUNT_ONLY | 23 | Has amount but no date/balance → partial split |
| NARRATION_CONT | 120 | No date, no amount → narration continuation line |
| HEADER | 1 | Column header row |
| BLANK | 0 | Empty / single token |

## 2. Fragment / Merge Detection

Split transactions detected: **0**
(TXN_ANCHOR immediately followed by AMOUNT_ORPHAN/AMOUNT_ONLY)


Merged rows detected: **1**


## 3. Transaction Block Analysis

TXN_ANCHOR rows:         82
TXN_ANchors with no amount (debit=null, credit=null): **0**


## 4. Narration Continuation Analysis — First 15 Transactions

### Row 23 | Page 1 | Date: `03/11/21`
Anchor: `03/11/21 | ATW.416021XXXXXX8811-S1ANPZ50-JALANDHAR | 0000000000009423 | 03/07/21 | 5,000.0`

Debit=5000.0  Credit=None  Balance=309919.1

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 24 | Page 1 | Date: `09/11/21`
Anchor: `09/11/21 | ATW-416021XXXXXX8811-S1ANPZ50- | JALANDHAR | 0000000000009754 | 09/07/21 | 5,00`

Debit=5000.0  Credit=None  Balance=304919.1

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 25 | Page 1 | Date: `07/11/21`
Anchor: `07/11/21 | UPI-SARABIT | SINGH-SARAB SINGH1994@OKHDF | 0000118816435251 | 07/07/21 | 10,00`

Debit=None  Credit=10000.0  Balance=314919.1

Following rows before next anchor: 2 (2 narration, 0 amount orphans)

  - [NARRATION_CONT] `CBANK-YES0002884-118816435251-RETURNFR`
  - [NARRATION_CONT] `OMSAKSHI`

### Row 28 | Page 1 | Date: `10/11/21`
Anchor: `10/11/21 | NWD-416021XXXXXX8811-B1020900- | JALANDHAR | 0000119113592357 | 10/07/21 | 10,0`

Debit=10000.0  Credit=None  Balance=304919.1

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 29 | Page 1 | Date: `10/11/21`
Anchor: `10/11/21 | POS 416021XXXXXX8S11PUNJABHIMACHALFI | 0000119111689299 | 10/07/21 | 1,800.00 |`

Debit=1800.0  Credit=None  Balance=303119.1

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 30 | Page 1 | Date: `12/11/21`
Anchor: `12/11/21 | ATW-416021XXXXXX8811-S1ANPZ50- | JALANDHAR | 0000000000001164 | 12/07/21 | 5,00`

Debit=5000.0  Credit=None  Balance=298119.1

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 31 | Page 1 | Date: `12/11/21`
Anchor: `12/11/21 | FUEL SURCHG416021******8811DT 10/07/21 | 0000119111689299 | 12/07/21 | 8.50 | 2`

Debit=8.5  Credit=None  Balance=298110.6

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 32 | Page 1 | Date: `16/11/21`
Anchor: `16/11/21 | ATW-416021XXXXX8811-P1DCHS03- | JALANDHAR | 0000000000009009 | 16/07/21 | 10.00`

Debit=10000.0  Credit=None  Balance=288110.6

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 33 | Page 1 | Date: `16/11/21`
Anchor: `16/11/21 | POS 416021XXXXXX8811 AKAL FILLING STA | 0000119716703637 | 16/07/21 | 1,900.00 `

Debit=1900.0  Credit=None  Balance=286210.6

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 34 | Page 1 | Date: `18/11/21`
Anchor: `18/11/21 | FUEL SURCHG416021******8811DT16/07/2 | 0000119716703637 | 18/07/21 | 8.97 | 285`

Debit=8.97  Credit=None  Balance=285201.63

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 35 | Page 1 | Date: `19/11/21`
Anchor: `19/11/21 | ATW416021XXXXXX8811-S1ANPZ50. | JALANDHAR | 0000000000002530 | 19/07/21 | 5,000`

Debit=5000.0  Credit=None  Balance=281201.63

Following rows before next anchor: 0 (0 narration, 0 amount orphans)


### Row 36 | Page 1 | Date: `23/11/21`
Anchor: `23/11/21 | RD BOOKED/INSTALLMENT PAID-S0400244209 | 000000000000000 | 23/07/21 | 1,000.00 `

Debit=1000.0  Credit=None  Balance=280201.63

Following rows before next anchor: 1 (1 narration, 0 amount orphans)

  - [NARRATION_CONT] `174KULDEEPSINGH`

### Row 38 | Page 1 | Date: `23/11/21`
Anchor: `23/11/21 | INST-ALERT CHG INC GST APR-JUN2O21-MIR21 | MIR2120090932007 | 23/07/21 | 17.70 `

Debit=17.7  Credit=None  Balance=280183.93

Following rows before next anchor: 1 (1 narration, 0 amount orphans)

  - [NARRATION_CONT] `20090932007`

### Row 40 | Page 1 | Date: `28/11/21`
Anchor: `28/11/21 | ADHOC STMT CHGS INCL GST 230721-MIR22207 | MIR2220708987972 | 28/07/21 | 118.00`

Debit=118.0  Credit=None  Balance=280065.93

Following rows before next anchor: 1 (1 narration, 0 amount orphans)

  - [NARRATION_CONT] `08987972`

### Row 42 | Page 1 | Date: `29/11/21`
Anchor: `29/11/21 | NWD-416021XXXXXX8811-A1191510- | JALANDHAR | 0000121013207091 | 29/07/21 | 8,00`

Debit=8000.0  Credit=None  Balance=272065.93

Following rows before next anchor: 0 (0 narration, 0 amount orphans)



## 5. Amount Ownership Audit — Rows Missing Amount

For each TXN_ANCHOR with no debit/credit, show all numeric tokens on that row:


## 6. Full OCR Row Dump (All 227 Rows)

| Idx | Page | y0 | Type | Tokens | Text |
|-----|------|----|------|--------|------|
| 0 | 1 | 118 | `NARRATION_CONT` | 1 | `PageNo1` |
| 1 | 1 | 177 | `NARRATION_CONT` | 4 | `YES | BANK | Accouat Branch | MAQSUDAN` |
| 2 | 1 | 224 | `AMOUNT_ONLY` | 2 | `Address | PN2MAQSUDAN` |
| 3 | 1 | 248 | `AMOUNT_ONLY` | 1 | `JALANDHAR 144001` |
| 4 | 1 | 266 | `NARRATION_CONT` | 1 | `PUNJAB` |
| 5 | 1 | 288 | `NARRATION_CONT` | 3 | `MRDARSHAN SINGH | City | JALANDHAR` |
| 6 | 1 | 306 | `NARRATION_CONT` | 2 | `State | PUNJAB` |
| 7 | 1 | 328 | `NARRATION_CONT` | 2 | `S/O SUCHA SINGH | Phonena` |
| 8 | 1 | 340 | `NARRATION_CONT` | 1 | `9815331111` |
| 9 | 1 | 354 | `NARRATION_CONT` | 3 | `VILLAGEKAHL WAN PO | OD Lmit | 0.00` |
| 10 | 1 | 372 | `NARRATION_CONT` | 1 | `Currency` |
| 11 | 1 | 387 | `NARRATION_CONT` | 2 | `BATHAL BHAI KE | INR` |
| 12 | 1 | 399 | `NARRATION_CONT` | 1 | `Email` |
| 13 | 1 | 415 | `NARRATION_CONT` | 2 | `TARN TARAN | Cust ID` |
| 14 | 1 | 429 | `NARRATION_CONT` | 1 | `DARSHANGILL1976@GMAILC` |
| 15 | 1 | 441 | `NARRATION_CONT` | 2 | `143401 | Account No` |
| 16 | 1 | 455 | `NARRATION_CONT` | 2 | `AC Open Date | OM` |
| 17 | 1 | 486 | `NARRATION_CONT` | 2 | `JOINT HOLDERS | Accouat Status` |
| 18 | 1 | 509 | `AMOUNT_ONLY` | 3 | `RIGS/NEFT IFSC | YESB0000071 | MICR144532002` |
| 19 | 1 | 528 | `AMOUNT_ONLY` | 3 | `Brarch Code | 0071 | Product Code 100` |
| 20 | 1 | 559 | `NARRATION_CONT` | 1 | `NominationRegistered` |
| 21 | 1 | 608 | `NARRATION_CONT` | 3 | `From01/11/2021 | To07/02/2022 | Statement of account` |
| 22 | 1 | 653 | `HEADER` | 7 | `Date | Narration | Chq/Ref.No. | Value Dt | Withdrawal Amt. | Deposit ` |
| 23 | 1 | 696 | `TXN_ANCHOR` | 6 | `03/11/21 | ATW.416021XXXXXX8811-S1ANPZ50-JALANDHAR | 0000000000009423 ` |
| 24 | 1 | 741 | `TXN_ANCHOR` | 7 | `09/11/21 | ATW-416021XXXXXX8811-S1ANPZ50- | JALANDHAR | 00000000000097` |
| 25 | 1 | 780 | `TXN_ANCHOR` | 7 | `07/11/21 | UPI-SARABIT | SINGH-SARAB SINGH1994@OKHDF | 000011881643525` |
| 26 | 1 | 828 | `NARRATION_CONT` | 1 | `CBANK-YES0002884-118816435251-RETURNFR` |
| 27 | 1 | 870 | `NARRATION_CONT` | 1 | `OMSAKSHI` |
| 28 | 1 | 910 | `TXN_ANCHOR` | 7 | `10/11/21 | NWD-416021XXXXXX8811-B1020900- | JALANDHAR | 00001191135923` |
| 29 | 1 | 945 | `TXN_ANCHOR` | 6 | `10/11/21 | POS 416021XXXXXX8S11PUNJABHIMACHALFI | 0000119111689299 | 1` |
| 30 | 1 | 995 | `TXN_ANCHOR` | 7 | `12/11/21 | ATW-416021XXXXXX8811-S1ANPZ50- | JALANDHAR | 00000000000011` |
| 31 | 1 | 1038 | `TXN_ANCHOR` | 6 | `12/11/21 | FUEL SURCHG416021******8811DT 10/07/21 | 0000119111689299 |` |
| 32 | 1 | 1080 | `TXN_ANCHOR` | 7 | `16/11/21 | ATW-416021XXXXX8811-P1DCHS03- | JALANDHAR | 000000000000900` |
| 33 | 1 | 1125 | `TXN_ANCHOR` | 6 | `16/11/21 | POS 416021XXXXXX8811 AKAL FILLING STA | 0000119716703637 | ` |
| 34 | 1 | 1167 | `TXN_ANCHOR` | 6 | `18/11/21 | FUEL SURCHG416021******8811DT16/07/2 | 0000119716703637 | 1` |
| 35 | 1 | 1212 | `TXN_ANCHOR` | 7 | `19/11/21 | ATW416021XXXXXX8811-S1ANPZ50. | JALANDHAR | 000000000000253` |
| 36 | 1 | 1257 | `TXN_ANCHOR` | 6 | `23/11/21 | RD BOOKED/INSTALLMENT PAID-S0400244209 | 000000000000000 | ` |
| 37 | 1 | 1299 | `NARRATION_CONT` | 1 | `174KULDEEPSINGH` |
| 38 | 1 | 1342 | `TXN_ANCHOR` | 6 | `23/11/21 | INST-ALERT CHG INC GST APR-JUN2O21-MIR21 | MIR2120090932007` |
| 39 | 1 | 1384 | `NARRATION_CONT` | 1 | `20090932007` |
| 40 | 1 | 1424 | `TXN_ANCHOR` | 6 | `28/11/21 | ADHOC STMT CHGS INCL GST 230721-MIR22207 | MIR2220708987972` |
| 41 | 1 | 1472 | `NARRATION_CONT` | 1 | `08987972` |
| 42 | 1 | 1514 | `TXN_ANCHOR` | 7 | `29/11/21 | NWD-416021XXXXXX8811-A1191510- | JALANDHAR | 00001210132070` |
| 43 | 1 | 1549 | `TXN_ANCHOR` | 7 | `31/11/21 | ATW-416021XXXXXX8811-S1ANPZ50 | JALANDHAR | 000000000000421` |
| 44 | 1 | 1594 | `TXN_ANCHOR` | 7 | `31/11/21 | ATW-416021XXXXXX8811-S1ANPZ50 | JALANDHAR | 000000000000421` |
| 45 | 1 | 1637 | `TXN_ANCHOR` | 7 | `01/12/21 | MPS-121310834669-NEXTBILLION | TECHNOLO-H | 000012131083466` |
| 46 | 1 | 1686 | `NARRATION_CONT` | 2 | `DFC-XXXXXXXXXXX7539-FUNDS | TRANSFER` |
| 47 | 1 | 1726 | `TXN_ANCHOR` | 7 | `03/12/21 | ATW-416021XXXXXX8811-E1AWLD06 | JALANDHAR | 000000000000985` |
| 48 | 1 | 1771 | `TXN_ANCHOR` | 6 | `04/12/21 | FEE-ATMCASH(21XN)31/07/21-AOR2221623221 | AOR2221623221299 ` |
| 49 | 1 | 1814 | `NARRATION_CONT` | 1 | `299` |
| 50 | 1 | 1854 | `TXN_ANCHOR` | 6 | `06/12/21 | POS416021XXXXXX8811 BHAR1 AIRTEL LI | 0000121836024214 | 06` |
| 51 | 1 | 1901 | `TXN_ANCHOR` | 6 | `07/12/21 | IMPS-121916330992-INDIA TOABROAD-UTIB-X | 0000121916330992 ` |
| 52 | 1 | 1943 | `NARRATION_CONT` | 1 | `XXXXXXXXXX6864-5000` |
| 53 | 1 | 2042 | `NARRATION_CONT` | 1 | `YES BANK LIMITED` |
| 54 | 1 | 2068 | `NARRATION_CONT` | 1 | `*Closing balance ncludes funds earmarked for hold and uncleared fund` |
| 55 | 1 | 2092 | `NARRATION_CONT` | 1 | `Contens of dhis statemens will be considered correct ifno errcr is rep` |
| 56 | 1 | 2125 | `NARRATION_CONT` | 1 | `State account branch GSIN:03AAACH2702H1ZA` |
| 57 | 1 | 2148 | `NARRATION_CONT` | 1 | `ax Registered` |
| 58 | 1 | 2163 | `NARRATION_CONT` | 1 | `Office Address:YES Bank HouseSeaapati Bapat Marg.Lower Parel,Mumbai 40` |
| 59 | 2 | 118 | `NARRATION_CONT` | 1 | `PageNo2` |
| 60 | 2 | 177 | `NARRATION_CONT` | 4 | `YES | BANK | Accouat Branch | MAQSUDAN` |
| 61 | 2 | 224 | `AMOUNT_ONLY` | 2 | `Address | PN2MAQSUDAN` |
| 62 | 2 | 248 | `AMOUNT_ONLY` | 1 | `JALANDHAR 144001` |
| 63 | 2 | 266 | `NARRATION_CONT` | 1 | `PUNJAB` |
| 64 | 2 | 288 | `NARRATION_CONT` | 3 | `MRDARSHAN SINGH | City | JALANDHAR` |
| 65 | 2 | 306 | `NARRATION_CONT` | 2 | `State | PUNJAB` |
| 66 | 2 | 328 | `NARRATION_CONT` | 2 | `S/O SUCHA SINGH | Phonena` |
| 67 | 2 | 340 | `NARRATION_CONT` | 1 | `9815331111` |
| 68 | 2 | 354 | `NARRATION_CONT` | 3 | `VILLAGE KAHL WAN PO | OD Limit | 0.00` |
| 69 | 2 | 372 | `NARRATION_CONT` | 1 | `Currency` |
| 70 | 2 | 387 | `NARRATION_CONT` | 2 | `BATHAL BHAI KE | INR` |
| 71 | 2 | 399 | `NARRATION_CONT` | 1 | `Email` |
| 72 | 2 | 415 | `NARRATION_CONT` | 2 | `TARN TARAN | Cust ID` |
| 73 | 2 | 427 | `NARRATION_CONT` | 1 | `DARSHANGILL1976@GMAILC` |
| 74 | 2 | 441 | `NARRATION_CONT` | 2 | `143401 | Account No` |
| 75 | 2 | 455 | `NARRATION_CONT` | 2 | `AC Open Date | OM` |
| 76 | 2 | 486 | `NARRATION_CONT` | 2 | `JOINT HOLDERS | Accouat Status` |
| 77 | 2 | 509 | `AMOUNT_ONLY` | 3 | `RIGS/NEFT IFSC | YESB0000071 | MICR144532002` |
| 78 | 2 | 531 | `AMOUNT_ONLY` | 3 | `Branch Code | 0071 | Product Code100` |
| 79 | 2 | 559 | `NARRATION_CONT` | 1 | `NominationRegistered` |
| 80 | 2 | 608 | `NARRATION_CONT` | 3 | `From01/11/2021 | To07/02/2022 | Statement of account` |
| 81 | 2 | 644 | `TXN_ANCHOR` | 6 | `08/12/21 | POS416021XXXXXX8811JAKUFILLING STA | 0000122009510996 | 08/` |
| 82 | 2 | 686 | `TXN_ANCHOR` | 6 | `10/12/21 | IMPS-122213350987-INDIA IOABROAD-UIIB-X | 0000122213350987 ` |
| 83 | 2 | 729 | `NARRATION_CONT` | 1 | `XXXXXXXXXX6864-20000` |
| 84 | 2 | 771 | `TXN_ANCHOR` | 6 | `10/12/21 | NWD-416021XXXXXX8811-IOBD5090-JALANDHAR | 0000122213094630 ` |
| 85 | 2 | 816 | `TXN_ANCHOR` | 6 | `14/12/21 | NWD-416021XXXXXX8811-92454003-PUNJAB | 0000122610065793 | 1` |
| 86 | 2 | 854 | `TXN_ANCHOR` | 6 | `14/12/21 | NWD-416021XXXXXX8811-924S4003-PUNJAB | 0000122610066493 | 1` |
| 87 | 2 | 901 | `TXN_ANCHOR` | 6 | `17/12/21 | CASH DEP JALANDHAR | 0000000000003372 | 17/08/21 | 20,000.0` |
| 88 | 2 | 943 | `TXN_ANCHOR` | 6 | `17/12/21 | UPI-HARMANPREETSINGH SO-PREETHARMAN9T79 | 0000122918666478 ` |
| 89 | 2 | 993 | `NARRATION_CONT` | 1 | `7@OKAX1S-PUNB0029610-122918666478-UPI` |
| 90 | 2 | 1031 | `TXN_ANCHOR` | 6 | `18/12/21 | IMPS P2P 121916330992#07/08/2021070821 | MIR2222743657167 |` |
| 91 | 2 | 1073 | `NARRATION_CONT` | 1 | `MIR2222743657167` |
| 92 | 2 | 1115 | `TXN_ANCHOR` | 6 | `18/12/21 | IMPSP2P 122213350987#10/08/2021100821 | MIR2222845817544 | ` |
| 93 | 2 | 1160 | `NARRATION_CONT` | 1 | `MIR2222845817544` |
| 94 | 2 | 1203 | `TXN_ANCHOR` | 6 | `19/12/21 | ATW-416021XXXXXX8811-S1ANPZ50-HOSHIARPUR | 0000000000007487` |
| 95 | 2 | 1243 | `TXN_ANCHOR` | 6 | `22/12/21 | NWD-416021XXXXXX8811-SPSBV018-MEHTIANA | 0000123411006462 |` |
| 96 | 2 | 1288 | `TXN_ANCHOR` | 6 | `24/08/21 | 50400244209174-RDINSTALLMENT-AUG2021 | 000000000000000 | 23` |
| 97 | 2 | 1325 | `TXN_ANCHOR` | 6 | `26/12/21 | POS 416021XXXXXX8811IRCTC | 0000123748004568 | 25/08/21 | 2` |
| 98 | 2 | 1372 | `TXN_ANCHOR` | 6 | `26/12/21 | POS416021XXXXXX8811IRCTC | 0000123767007332 | 25/08/21 | 27` |
| 99 | 2 | 1417 | `TXN_ANCHOR` | 6 | `26/12/21 | POS 416021XXXXXX8811 GOVINDA MEDICENI | 0000000000002195 | ` |
| 100 | 2 | 1460 | `TXN_ANCHOR` | 6 | `26/12/21 | POS416021XXXXXX8811 ANKITMEDICOS | 0000000000001978 | 25/08` |
| 101 | 2 | 1502 | `TXN_ANCHOR` | 6 | `26/12/21 | NWD-416021XXXXXX8811-N9011900-CENTRALDEL | 0000123811558034` |
| 102 | 2 | 1545 | `NARRATION_CONT` | 1 | `HI` |
| 103 | 2 | 1590 | `TXN_ANCHOR` | 6 | `28/12/21 | POS416021XXXXXX8811IRCTC | 0000123828038123 | 26/08/21 | 30` |
| 104 | 2 | 1624 | `TXN_ANCHOR` | 6 | `29/12/21 | POS416021XXXXXX8811IRCTC | 0000123808311945 | 26/08/21 | 30` |
| 105 | 2 | 1674 | `TXN_ANCHOR` | 6 | `30/12/21 | FEE-ATMCASH(1TXN)26/08/21-AOR2223968458 | AOR2223968458779 ` |
| 106 | 2 | 1717 | `NARRATION_CONT` | 1 | `779` |
| 107 | 2 | 1757 | `TXN_ANCHOR` | 6 | `30/12/21 | POS REF416021******8811-08/28IRCTC8550 | 000000000000000 | ` |
| 108 | 2 | 1799 | `TXN_ANCHOR` | 6 | `30/12/21 | POS REF416021******8811-08/28 IRCTC8550 | 000000000000000 |` |
| 109 | 2 | 1847 | `TXN_ANCHOR` | 6 | `31/12/21 | UPI-BILLDESKTEZ-BILLDESKELECTRICITY@ICI | 0000124355881949 ` |
| 110 | 2 | 1891 | `NARRATION_CONT` | 1 | `CI-ICIC0000955-124355881949-UPI` |
| 111 | 2 | 1934 | `TXN_ANCHOR` | 6 | `31/12/21 | UPI-BILLDESKTEZ-BILLDESKELECIRICIIY@ICI | 0000124355926169 ` |
| 112 | 2 | 1979 | `NARRATION_CONT` | 1 | `CI-ICIC0000955-124355926169-UPI` |
| 113 | 2 | 2047 | `NARRATION_CONT` | 1 | `YESBANK LIMITED` |
| 114 | 2 | 2068 | `NARRATION_CONT` | 1 | `*Closing balance ncludes funds earmarked for hold and uncleared fund` |
| 115 | 2 | 2092 | `NARRATION_CONT` | 1 | `Contens of dhis statemens will be considered correct ifno errcr is rep` |
| 116 | 2 | 2125 | `NARRATION_CONT` | 1 | `State account branch GSIN:03AAACH2702H1ZA` |
| 117 | 2 | 2148 | `NARRATION_CONT` | 1 | `ax Registered` |
| 118 | 2 | 2163 | `NARRATION_CONT` | 1 | `Office Address:YES Bank HouseSeaapati Bapat Marg.Lower Parel,Mumbai 40` |
| 119 | 3 | 118 | `NARRATION_CONT` | 1 | `PageNo3` |
| 120 | 3 | 177 | `NARRATION_CONT` | 4 | `YES | BANK | Accouat Branch | MAQSUDAN` |
| 121 | 3 | 224 | `AMOUNT_ONLY` | 2 | `Address | PN2MAQSUDAN` |
| 122 | 3 | 248 | `AMOUNT_ONLY` | 1 | `JALANDHAR 144001` |
| 123 | 3 | 266 | `NARRATION_CONT` | 1 | `PUNJAB` |
| 124 | 3 | 288 | `NARRATION_CONT` | 3 | `MRDARSHAN SINGH | City | JALANDHAR` |
| 125 | 3 | 306 | `NARRATION_CONT` | 2 | `State | PUNJAB` |
| 126 | 3 | 328 | `NARRATION_CONT` | 2 | `S/O SUCHA SINGH | Phonena` |
| 127 | 3 | 340 | `NARRATION_CONT` | 1 | `9815331111` |
| 128 | 3 | 354 | `NARRATION_CONT` | 3 | `VILLAGEKAHL WAN PO | OD Lmit | 0.00` |
| 129 | 3 | 372 | `NARRATION_CONT` | 1 | `Currency` |
| 130 | 3 | 387 | `NARRATION_CONT` | 2 | `BATHAL BHAI KE | INR` |
| 131 | 3 | 399 | `NARRATION_CONT` | 1 | `Email` |
| 132 | 3 | 415 | `NARRATION_CONT` | 2 | `TARN TARAN | Cust ID` |
| 133 | 3 | 429 | `NARRATION_CONT` | 1 | `DARSHANGILL197GGGMAILC` |
| 134 | 3 | 441 | `NARRATION_CONT` | 2 | `143401 | Account No` |
| 135 | 3 | 455 | `NARRATION_CONT` | 2 | `AC Open Date | OM` |
| 136 | 3 | 488 | `NARRATION_CONT` | 2 | `JOINT HOLDERS | Accouat Status` |
| 137 | 3 | 507 | `AMOUNT_ONLY` | 3 | `RIGS/NEFT IFSC | YESB0000071 | MICR144532002` |
| 138 | 3 | 528 | `AMOUNT_ONLY` | 3 | `Brarch Code | 0071 | Product Code 100` |
| 139 | 3 | 559 | `NARRATION_CONT` | 1 | `NominationRegistered` |
| 140 | 3 | 608 | `NARRATION_CONT` | 3 | `From01/11/2021 | To07/02/2022 | Statement of account` |
| 141 | 3 | 644 | `TXN_ANCHOR` | 6 | `01/01/22 | 1545181226/TECHWIESOFTWAREPVTLT | 0000212444075221 | 01/09/` |
| 142 | 3 | 681 | `TXN_ANCHOR` | 6 | `01/01/22 | POS REF416021*****8811-09/01IRCTC3751 | 000000000000000 | 0` |
| 143 | 3 | 729 | `TXN_ANCHOR` | 6 | `01/01/22 | POS REF416021******8811-09/01IRCTC3751 | 000000000000000 | ` |
| 144 | 3 | 771 | `TXN_ANCHOR` | 6 | `01/01/22 | KQRHK74KBNGKLNOVCU/PAYUDELHIINTSCH | 0000212444363214 | 01/` |
| 145 | 3 | 816 | `TXN_ANCHOR` | 6 | `02/01/22 | CRVPOS-416021******8811-0831-IRCTC | 000000000000000 | 02/0` |
| 146 | 3 | 856 | `TXN_ANCHOR` | 6 | `02/01/22 | CRVPOS-416021******811-0831IRCTC | 000000000000000 | 02/09/` |
| 147 | 3 | 901 | `TXN_ANCHOR` | 6 | `03/01/22 | CASH DEP RAJPUR BHAIA | 0000000000003372 | 03/09/21 | 45,00` |
| 148 | 3 | 946 | `TXN_ANCHOR` | 6 | `03/01/22 | ATW-416021XXXXXX8811-S1ANPJ70-HOSHIARPUR | 0000000000001672` |
| 149 | 3 | 988 | `TXN_ANCHOR` | 6 | `03/01/22 | UPI-SAKSHI-KAURSAKSHI230@OKYESBANK-INDE | 0000124603397994 ` |
| 150 | 3 | 1033 | `NARRATION_CONT` | 1 | `0000284-124603397994-UPI` |
| 151 | 3 | 1073 | `TXN_ANCHOR` | 6 | `07/01/22 | 1551506822/TECHWIESOFTWAREPVTLT | 0000212509116500 | 07/09/` |
| 152 | 3 | 1115 | `TXN_ANCHOR` | 6 | `07/01/22 | FT-RAJINDER KUMAR CR-50100142463671 | 0000000000000001 | 07` |
| 153 | 3 | 1160 | `NARRATION_CONT` | 1 | `RANJEET KAUR` |
| 154 | 3 | 1203 | `TXN_ANCHOR` | 6 | `09/01/22 | CASH DEP RAJPUR BHAIA | 0000000000003372 | 09/09/21 | 58,00` |
| 155 | 3 | 1248 | `TXN_ANCHOR` | 6 | `10/01/22 | UPI-NAVDEEP | 0000125393150928 | 10/09/21 | 11,000.00 | 356` |
| 156 | 3 | 1292 | `NARRATION_CONT` | 1 | `KUMAR-NAVDEEP KAYASTHA-I@OKH` |
| 157 | 3 | 1335 | `NARRATION_CONT` | 1 | `DFCBANK-YES0001330-125393150928-UPI` |
| 158 | 3 | 1375 | `TXN_ANCHOR` | 6 | `10/01/22 | POS 416021XXXXXX8811 JAKU FILLING STA | 0000125309508672 | ` |
| 159 | 3 | 1420 | `TXN_ANCHOR` | 6 | `13/01/22 | 50100142463671-TPT-PAYMENT-RANJEET KAU | 0000000192638209 |` |
| 160 | 3 | 1465 | `NARRATION_CONT` | 1 | `R` |
| 161 | 3 | 1507 | `TXN_ANCHOR` | 6 | `14/01/22 | UPI-SRINEEL KANTH GARME-GPAY-1117423011 | 0000125746120439 ` |
| 162 | 3 | 1552 | `NARRATION_CONT` | 1 | `8@OKBIZAXIS-UTIB0000000-125746120439-UPI` |
| 163 | 3 | 1589 | `TXN_ANCHOR` | 6 | `15/01/22 | CASH DEP RAJPUR BHAIA | 0000000000003372 | 15/09/21 | 26,00` |
| 164 | 3 | 1634 | `TXN_ANCHOR` | 6 | `16/01/22 | NWD-416021XXXXXX8811-A1191510-HOSHIARPUR | 0000125913212868` |
| 165 | 3 | 1677 | `TXN_ANCHOR` | 6 | `19/01/22 | ATW-416021XXXXXX8811-S1ANPZ50-HOSHIARPUR UPI | 000000000000` |
| 166 | 3 | 1722 | `TXN_ANCHOR` | 6 | `21/01/22 | EURONEIGPAY-EURONE TGPAYPAY@ICICI-IC | 0000126432477543 | 2` |
| 167 | 3 | 1762 | `NARRATION_CONT` | 1 | `IC0000001-126432477543-UPI` |
| 168 | 3 | 1809 | `TXN_ANCHOR` | 6 | `23/01/22 | IMPS-126615382235-RANJEETKAUR-YES-XXXX | 0000126615382235 |` |
| 169 | 3 | 1847 | `NARRATION_CONT` | 1 | `XXXXXX3671-45000` |
| 170 | 3 | 1894 | `TXN_ANCHOR` | 6 | `23/01/22 | CASHDEP RAJPUR BHAIA | 0000000000003372 | 23/09/21 | 19,000` |
| 171 | 3 | 1936 | `TXN_ANCHOR` | 6 | `24/01/22 | 50400244209174-RD INSTALLMENT-SEP 2021 | 000000000000000 | ` |
| 172 | 3 | 1976 | `TXN_ANCHOR` | 6 | `25/01/22 | UPI-NARESH KAMAL SO SH G-KEHAR9S125-1@OK | 0000126886096251` |
| 173 | 3 | 2042 | `NARRATION_CONT` | 1 | `YES BANK LIMITED` |
| 174 | 3 | 2068 | `NARRATION_CONT` | 1 | `*Closing balance ncludes funds earmarked for hold and uncleared fund` |
| 175 | 3 | 2092 | `NARRATION_CONT` | 1 | `Contens of dhis statemens will be considered correct ifno errcr is rep` |
| 176 | 3 | 2125 | `NARRATION_CONT` | 1 | `State account branch GSIN:03AAACH2702H1ZA` |
| 177 | 3 | 2148 | `NARRATION_CONT` | 1 | `x Registered` |
| 178 | 3 | 2163 | `NARRATION_CONT` | 1 | `Office Address:YES Bank HouseSeaapati Bapat Marg.Lower Parel,Mumbai 40` |
| 179 | 4 | 120 | `NARRATION_CONT` | 1 | `Page No4` |
| 180 | 4 | 171 | `NARRATION_CONT` | 4 | `YES | BANK | Accouat Branch | MAQSUDAN` |
| 181 | 4 | 224 | `AMOUNT_ONLY` | 2 | `Address | VPO RAJPUR BHAIANKHASRA NO.44/3/1/` |
| 182 | 4 | 245 | `AMOUNT_ONLY` | 1 | `10-44/3/1/2/10-1244//3/1/` |
| 183 | 4 | 266 | `AMOUNT_ONLY` | 1 | `2/20-6).IEH AND DIST-HOSHIARPUR` |
| 184 | 4 | 290 | `AMOUNT_ONLY` | 3 | `MR DARSHAN SINGH | City | JALANDHAR 144001` |
| 185 | 4 | 311 | `NARRATION_CONT` | 2 | `State | PUNJAB` |
| 186 | 4 | 328 | `AMOUNT_ONLY` | 3 | `S/O SUCHA SINGH | Phonenc | 9815331111` |
| 187 | 4 | 351 | `NARRATION_CONT` | 3 | `VILLAGE KAHLWAN PO | OD Lmit | 0.00` |
| 188 | 4 | 372 | `NARRATION_CONT` | 2 | `Currency | INR` |
| 189 | 4 | 389 | `AMOUNT_ONLY` | 2 | `BATHAL BHAI KE | DARSHANGILL1976@GMAIL.COM` |
| 190 | 4 | 399 | `NARRATION_CONT` | 1 | `Email` |
| 191 | 4 | 415 | `AMOUNT_ONLY` | 3 | `TARN TARAN | Cust ID | 52990038` |
| 192 | 4 | 439 | `AMOUNT_ONLY` | 3 | `143401 | Account No | S0100025390700 PRIME` |
| 193 | 4 | 465 | `AMOUNT_ONLY` | 2 | `AC Open Date | 04/12/2013` |
| 194 | 4 | 483 | `NARRATION_CONT` | 3 | `JOINT HOLDERS | Accouat Status | Regular` |
| 195 | 4 | 509 | `AMOUNT_ONLY` | 3 | `RIGS/NEFT IFSC | YESB0000071 | MICR144532002` |
| 196 | 4 | 528 | `AMOUNT_ONLY` | 3 | `Brarch Code | 1132 | Product Code100` |
| 197 | 4 | 559 | `NARRATION_CONT` | 1 | `NominationRegistered` |
| 198 | 4 | 608 | `NARRATION_CONT` | 3 | `From01/11/2021 | To04/09/2022 | Statement of account` |
| 199 | 4 | 639 | `NARRATION_CONT` | 1 | `YESBANK-UBIN0909933-126886096251-UPI` |
| 200 | 4 | 674 | `TXN_ANCHOR` | 5 | `25/01/22 | IMPS-126815314563-RANJEET KAUR-YES- | 000012681531456325/09` |
| 201 | 4 | 703 | `NARRATION_CONT` | 1 | `XXXX` |
| 202 | 4 | 738 | `NARRATION_CONT` | 1 | `XXXXXX3671-10000` |
| 203 | 4 | 766 | `TXN_ANCHOR` | 5 | `28/01/22 | CASHDEP RAJPUR BHAIA | 000000000000337228/09/21 | 19,000.00` |
| 204 | 4 | 802 | `TXN_ANCHOR` | 5 | `30/01/22 | POS416021XXXXXX8811MRBPCLFILLING | 0000000000000616 30/09/2` |
| 205 | 4 | 835 | `TXN_ANCHOR` | 6 | `01/02/22 | CREDIT INTEREST CAPITALISED | 000000000000000 | 30/09/21 | ` |
| 206 | 4 | 866 | `TXN_ANCHOR` | 5 | `01/02/22 | POS416021XXXXXX8811 BHARTIAIRTEL LT | 000012740455186901/10` |
| 207 | 4 | 903 | `TXN_ANCHOR` | 5 | `03/02/22 | NWD-416021XXXXXX8811-A1191510- | 000012761621560303/10/21 |` |
| 208 | 4 | 934 | `NARRATION_CONT` | 1 | `HOSHIARPUR` |
| 209 | 4 | 962 | `TXN_ANCHOR` | 5 | `04/02/22 | BRN CASH TXN CHGS INCLGST280921-MIR222 | MIR222753683353504` |
| 210 | 4 | 1000 | `NARRATION_CONT` | 1 | `7536833535` |
| 211 | 4 | 1031 | `TXN_ANCHOR` | 5 | `04/02/22 | POSREF416021******8811-10/02_MRBPCL | 000000000000000  04/1` |
| 212 | 4 | 1064 | `TXN_ANCHOR` | 5 | `09/02/22 | ATW-416021XXXXXX8811-S1ANPZ50- | 0000000000006416 06/10/21 ` |
| 213 | 4 | 1094 | `NARRATION_CONT` | 1 | `HOSHIARPUR` |
| 214 | 4 | 1122 | `TXN_ANCHOR` | 5 | `09/02/22 | NWD-416021XXXXXX8811-N3342100- | 000012801296015207/10/21 |` |
| 215 | 4 | 1156 | `NARRATION_CONT` | 1 | `HOSHIARPUR` |
| 216 | 4 | 1186 | `TXN_ANCHOR` | 5 | `07/02/22 | ATW-416021XXXXXX8811-S1ANPZ50- | 000000000000681708/10/21 |` |
| 217 | 4 | 1215 | `NARRATION_CONT` | 1 | `HOSHIARPUR` |
| 218 | 4 | 1240 | `AMOUNT_ORPHAN` | 4 | `07/02/22UPI-HARPREET SINGH- | 000012860877458713/10/21 | 25,000.00 | 4` |
| 219 | 4 | 1276 | `NARRATION_CONT` | 1 | `07HARMANHAR@OKSBI-SB` |
| 220 | 4 | 1307 | `NARRATION_CONT` | 1 | `IN0016901-128608774587-UPI` |
| 221 | 4 | 1335 | `TXN_ANCHOR` | 5 | `07.09/22 | CASHDEP | 0000000000003372 07/02/2022 | 40,000.00 | 5,29,85` |
| 222 | 4 | 1722 | `NARRATION_CONT` | 1 | `YES BANK LIMIIED` |
| 223 | 4 | 1745 | `NARRATION_CONT` | 1 | `*Closmg balance includes funds earmarked for hold and rncleared funds` |
| 224 | 4 | 1766 | `NARRATION_CONT` | 2 | `Couterts of ths statemes will be cosderedcorrect ifno eror is reported` |
| 225 | 4 | 1783 | `NARRATION_CONT` | 1 | `State account branch CSTN:03AAACH272H1ZA` |
| 226 | 4 | 1801 | `NARRATION_CONT` | 3 | `YES Bank GSTIN aunber dctails are ava lablc at https | .YESbank | cdOf` |

## 7. Root Cause Analysis

- TXN_ANCHOR rows:           82
- Amount orphan rows:         24  ← amounts OCR'd on separate rows from dates
- Narration continuation rows:120  ← multi-line narrations producing extra rows
- Anchors missing amount:     0  ← anchors where no debit/credit was claimed
- Fragment pairs detected:    0  ← anchor + orphan adjacent pairs

**HYPOTHESIS SUPPORTED:** Row fragmentation is occurring.

The parser treats each OCR row as a separate block.
Multi-line narrations and amount-row splits produce blocks with:
  - date but no amount (anchor orphaned from its amount row)
  - amount but no date (amount orphaned from its date row)
These are rejected as `no_debit_or_credit` and `no_date` respectively.
