# BOTH_DEBIT_AND_CREDIT Root Cause Audit

**Total Rejects Analysed:** 229

## Classification Results
- **BALANCE_STOLEN_BY_CREDIT**: 223
- **TRUE_DOUBLE_AMOUNT**: 6

## Detailed Traces (Sample)
```json
{
  "pdf": "axis.pdf",
  "date": "30-10-2021",
  "numbers": [
    30.0,
    29.5,
    696.5,
    178.0,
    23015690654.0,
    1.0,
    3.0,
    10000.0,
    10696.0,
    230456913471.0
  ],
  "debit_candidate": 29.5,
  "credit_candidate": 10000.0,
  "balance_candidate": 696.5,
  "balance_suffix": "null",
  "rightmost_numeric": 178.0,
  "reject_reason": "both_debit_and_credit",
  "category": "TRUE_DOUBLE_AMOUNT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "30/11/2024",
  "numbers": [
    30112024.0,
    922010016723931.0,
    126.0,
    661.0,
    210.78,
    367592237875.0
  ],
  "debit_candidate": 661.0,
  "credit_candidate": 210.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 210.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "30-11-2024",
  "numbers": [
    30.0,
    126.0,
    9617.0,
    9827.78,
    150810110022458.0,
    330408662255.0
  ],
  "debit_candidate": 9617.0,
  "credit_candidate": 9827.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 9827.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "30-11-2024",
  "numbers": [
    30.0,
    126.0,
    2797.0,
    12624.78,
    50100221800028.0,
    2024.0,
    251675.0
  ],
  "debit_candidate": 2797.0,
  "credit_candidate": 12624.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 12624.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "02-12-2024",
  "numbers": [
    2.0,
    126.0,
    43840.0,
    56464.78,
    33273316893.0,
    699411267300.0
  ],
  "debit_candidate": 43840.0,
  "credit_candidate": 56464.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 56464.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "02/12/2024",
  "numbers": [
    2122024.0,
    2261100000025.0,
    126.0,
    150.0,
    56314.78,
    226683506101.0
  ],
  "debit_candidate": 150.0,
  "credit_candidate": 56314.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 56314.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "02/12/2024",
  "numbers": [
    2122024.0,
    50200080420.0,
    126.0,
    200.0,
    56114.78,
    87.0,
    433870809844.0
  ],
  "debit_candidate": 200.0,
  "credit_candidate": 56114.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 56114.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "03/12/2024",
  "numbers": [
    3122024.0,
    126.0,
    10083.0,
    46031.78,
    2267800000666.0,
    63803760385.0,
    126.0,
    60.0,
    45971.78
  ],
  "debit_candidate": 10083.0,
  "credit_candidate": 46031.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 46031.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "03/12/2024",
  "numbers": [
    3122024.0,
    77770137878068.0,
    126.0,
    1000.0,
    44971.78,
    456675532376.0,
    44891.78
  ],
  "debit_candidate": 1000.0,
  "credit_candidate": 44971.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 44971.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "04/12/2024",
  "numbers": [
    4122024.0,
    126.0,
    1388.0,
    43503.78,
    77770137878068.0,
    622978320823.0,
    5000.0
  ],
  "debit_candidate": 1388.0,
  "credit_candidate": 43503.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 43503.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "04/12/2024",
  "numbers": [
    4122024.0,
    126.0,
    70.0,
    38433.78,
    309022685560.0,
    709669024986.0
  ],
  "debit_candidate": 70.0,
  "credit_candidate": 38433.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 38433.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "04/12/2024",
  "numbers": [
    4122024.0,
    226110000.0,
    126.0,
    902.0,
    37531.78,
    25.0,
    298044707051.0
  ],
  "debit_candidate": 902.0,
  "credit_candidate": 37531.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 37531.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "05/12/2024",
  "numbers": [
    5122024.0,
    138202000701.0,
    126.0,
    260.0,
    37271.78,
    30.0,
    398094362189.0
  ],
  "debit_candidate": 260.0,
  "credit_candidate": 37271.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 37271.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "05/12/2024",
  "numbers": [
    5122024.0,
    126.0,
    1000.0,
    36271.78,
    50100478383644.0,
    707756270844.0
  ],
  "debit_candidate": 1000.0,
  "credit_candidate": 36271.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 36271.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "06/12/2024",
  "numbers": [
    6122024.0,
    142500000005.0,
    126.0,
    1345.0,
    34926.78,
    1.0,
    319367103534.0
  ],
  "debit_candidate": 1345.0,
  "credit_candidate": 34926.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 34926.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "06/12/2024",
  "numbers": [
    6122024.0,
    126.0,
    50.0,
    34876.78,
    1425000.0,
    51.0
  ],
  "debit_candidate": 50.0,
  "credit_candidate": 34876.78,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 34876.78,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/02/2025",
  "numbers": [
    15022025.0,
    42.0,
    230.0,
    29019.71,
    63.0,
    485038794722.0,
    42.0,
    50.0,
    28969.71
  ],
  "debit_candidate": 230.0,
  "credit_candidate": 29019.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 29019.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/02/2025",
  "numbers": [
    15022025.0,
    81818.0,
    42.0,
    50.0,
    28769.71,
    4441.0,
    696203532532.0
  ],
  "debit_candidate": 50.0,
  "credit_candidate": 28769.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 28769.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/02/2025",
  "numbers": [
    15022025.0,
    42.0,
    270.0,
    28499.71,
    789735340.0,
    117160233738.0
  ],
  "debit_candidate": 270.0,
  "credit_candidate": 28499.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 28499.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/02/2025",
  "numbers": [
    15022025.0,
    3.0,
    42.0,
    69.0,
    28430.71,
    8805.0,
    3.0,
    100011330070.0
  ],
  "debit_candidate": 69.0,
  "credit_candidate": 28430.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 28430.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/02/2025",
  "numbers": [
    16022025.0,
    499.0,
    42.0,
    149.0,
    28281.71,
    234694710896.0
  ],
  "debit_candidate": 149.0,
  "credit_candidate": 28281.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 28281.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "17/02/2025",
  "numbers": [
    17022025.0,
    621000.0,
    42.0,
    10000.0,
    18281.71,
    2.962961000503006e+17,
    229830758673.0
  ],
  "debit_candidate": 10000.0,
  "credit_candidate": 18281.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 18281.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "18/02/2025",
  "numbers": [
    18022025.0,
    729.0,
    42.0,
    200.0,
    18081.71,
    798714128642.0
  ],
  "debit_candidate": 200.0,
  "credit_candidate": 18081.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 18081.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "20/02/2025",
  "numbers": [
    20022025.0,
    2691.0,
    42.0,
    200.0,
    17881.71,
    824388552189.0
  ],
  "debit_candidate": 200.0,
  "credit_candidate": 17881.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 17881.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "20/02/2025",
  "numbers": [
    20022025.0,
    42.0,
    250.0,
    17631.71,
    2669763231.0,
    192.0,
    505159228448.0
  ],
  "debit_candidate": 250.0,
  "credit_candidate": 17631.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 17631.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "20/02/2025",
  "numbers": [
    20022025.0,
    22.0,
    42.0,
    456.0,
    17175.71,
    186372889738.0
  ],
  "debit_candidate": 456.0,
  "credit_candidate": 17175.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 17175.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "22/02/2025",
  "numbers": [
    22022025.0,
    6533.0,
    42.0,
    500.0,
    16675.71,
    331.0,
    505545079762.0
  ],
  "debit_candidate": 500.0,
  "credit_candidate": 16675.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 16675.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "24-02-2025",
  "numbers": [
    24.0,
    49.0,
    2565.0,
    19240.71,
    505533525866.0
  ],
  "debit_candidate": 2565.0,
  "credit_candidate": 19240.71,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 19240.71,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "24/02/2025",
  "numbers": [
    24022025.0,
    42.0,
    1014.12,
    18226.59,
    99.344812,
    505636343834.0
  ],
  "debit_candidate": 1014.12,
  "credit_candidate": 18226.59,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 18226.59,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "25/02/2025",
  "numbers": [
    25022025.0,
    99.0,
    42.0,
    5.0,
    18221.59
  ],
  "debit_candidate": 5.0,
  "credit_candidate": 18221.59,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 18221.59,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    993564.0,
    126.0,
    5552.06,
    48006.29,
    615950323312134.0,
    493482955818.0
  ],
  "debit_candidate": 5552.06,
  "credit_candidate": 48006.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 48006.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    520101198.0,
    126.0,
    4000.0,
    44006.29,
    44980.0,
    942416199884.0
  ],
  "debit_candidate": 4000.0,
  "credit_candidate": 44006.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 44006.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    8002261100000025.0,
    126.0,
    600.0,
    43406.29,
    307007516611.0
  ],
  "debit_candidate": 600.0,
  "credit_candidate": 43406.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 43406.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    918020110872063.0,
    126.0,
    550.0,
    42856.29,
    558162894396.0
  ],
  "debit_candidate": 550.0,
  "credit_candidate": 42856.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 42856.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    300.0,
    42556.29,
    6043103300.0,
    126.0,
    311689823016.0
  ],
  "debit_candidate": 300.0,
  "credit_candidate": 42556.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 42556.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    50200023494088.0,
    126.0,
    1268.0,
    41288.29,
    205540452119.0
  ],
  "debit_candidate": 1268.0,
  "credit_candidate": 41288.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 41288.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    1253220002.0,
    126.0,
    2800.0,
    38488.29,
    8534.0,
    432053615417.0
  ],
  "debit_candidate": 2800.0,
  "credit_candidate": 38488.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 38488.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "15/11/2024",
  "numbers": [
    15112024.0,
    126.0,
    149.0,
    38339.29,
    50200027864076.0,
    199585816648.0
  ],
  "debit_candidate": 149.0,
  "credit_candidate": 38339.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 38339.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    1425000.0,
    126.0,
    80.0,
    38259.29,
    51.0,
    432109058358.0
  ],
  "debit_candidate": 80.0,
  "credit_candidate": 38259.29,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 38259.29,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    126.0,
    226.79,
    38032.5,
    1092787575.0,
    988168424782.0
  ],
  "debit_candidate": 226.79,
  "credit_candidate": 38032.5,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 38032.5,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    1425000000051.0,
    126.0,
    60.0,
    37972.5,
    166949278791.0
  ],
  "debit_candidate": 60.0,
  "credit_candidate": 37972.5,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 37972.5,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    142500000005.0,
    126.0,
    200.0,
    37772.5,
    1.0,
    249779205937.0
  ],
  "debit_candidate": 200.0,
  "credit_candidate": 37772.5,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 37772.5,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    2261100000025.0,
    126.0,
    4195.8,
    33576.7,
    797.0,
    82406366382.0
  ],
  "debit_candidate": 4195.8,
  "credit_candidate": 33576.7,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 33576.7,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    1400.0,
    31920100560.0,
    126.0,
    32176.7,
    6.0,
    652413615740.0
  ],
  "debit_candidate": 1400.0,
  "credit_candidate": 32176.7,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 32176.7,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/11/2024",
  "numbers": [
    16112024.0,
    5020009190515.0,
    126.0,
    578.0,
    31598.7,
    5.0,
    432209972933.0,
    126.0
  ],
  "debit_candidate": 578.0,
  "credit_candidate": 31598.7,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 31598.7,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "17/11/2024",
  "numbers": [
    17112024.0,
    238.36,
    31360.34,
    1092787575.0,
    392318523224.0
  ],
  "debit_candidate": 238.36,
  "credit_candidate": 31360.34,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 31360.34,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "17/11/2024",
  "numbers": [
    17112024.0,
    126.0,
    583.78,
    30776.56,
    10001291013.0,
    359.0,
    897093236706.0
  ],
  "debit_candidate": 583.78,
  "credit_candidate": 30776.56,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 30776.56,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "17/11/2024",
  "numbers": [
    17112024.0,
    126.0,
    2470.0,
    28306.56,
    308513289.0,
    342375706461.0
  ],
  "debit_candidate": 2470.0,
  "credit_candidate": 28306.56,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 28306.56,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "17/11/2024",
  "numbers": [
    17112024.0,
    126.0,
    350.0,
    28956.56,
    1425000000051.0
  ],
  "debit_candidate": 350.0,
  "credit_candidate": 28956.56,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 28956.56,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```
```json
{
  "pdf": "BOI_SAVINGS_SCANNED.pdf",
  "date": "16/03/2025",
  "numbers": [
    16032025.0,
    42.0,
    149.0,
    2923.59,
    544222653062.0
  ],
  "debit_candidate": 149.0,
  "credit_candidate": 2923.59,
  "balance_candidate": null,
  "balance_suffix": "CR",
  "rightmost_numeric": 2923.59,
  "reject_reason": "both_debit_and_credit",
  "category": "BALANCE_STOLEN_BY_CREDIT"
}
```