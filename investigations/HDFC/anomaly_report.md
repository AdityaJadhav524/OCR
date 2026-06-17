# HDFC Anomaly Report

Total Transactions: 107
Total Rejects: 14
Total Anomalies: 27

### Txn 1 - 17/05/25
Narration: HDFC BANK LIMITED Contes of this statemen will be considered correct if ao error is reported within 30 days of receipt of statemea.The address on this staemeat is that ou secord with the Bank as at the day of requestig *Closing balance includes funds earmarked for hold and uncleared funds Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement UPI-RUPALI MAHADEV 17/05/25
Debit: 30.0 | Credit: None | Balance: 728662.39
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '728.662.39', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 2 - 30/05/25
Narration: UPI-SHIVAJI ASHOK BHARIS-7798539582@YBL~ ONE SBIN0008891-380109783452.PAYMENTFROMPH 30/05/25
Debit: 800.0 | Credit: None | Balance: 693893.42
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0001', 'diff': 33968.97, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -33968.97'}

### Txn 3 - 30/05/25
Narration: 3005/25 UPI-MR RANVUAY KUMAR RANVJAYK262@OK IN-PAYIMQRIFHYLH2FHT@PAYTM UPI-SAI PARK ESS AXIS-CBIN0282444-018785526161-CLOTHES PR YESB0PTMUPI-338148174038-THALI 30/05/25 30/05/25
Debit: 70.0 | Credit: None | Balance: 693823.42
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '693.823.42', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 4 - 30/05/25
Narration: UPI-MR LALIT KUMAR PUK-Q754238133@YBL YESB0YBLUPI-052855723886-CHOCOLATE 30/05/25
Debit: 100.0 | Credit: None | Balance: 693443.42
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0002', 'diff': 280.0, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -280.0'}

### Txn 5 - 23/05/25
Narration: RAIMAN-Q991665194@YBL UPI-KUMARMAHADEV YESB0YBLUPI-502664328163-SANDWICH 23/05/25
Debit: 80.0 | Credit: None | Balance: 701079.52
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0003', 'diff': 9355.82, 'affected_rows': [], 'detail': 'Unexplained ledger drift of 9355.82'}

### Txn 6 - 24/05/25
Narration: 010110PEFY4G2LM3@PAYTM-YESB0PIMUPI-37833 PAYTMQR28100505 UPI-SURESH DHANAYAKUMAR 3119179-AMRAKHAND 24/05/25
Debit: 55.0 | Credit: None | Balance: 700452.52
Suspicious Fields:
- balance: {'reason': 'POWER_OF_TEN_DRIFT', 'severity': 'HIGH', 'diff': 10.0, 'magnitude': 1, 'detail': 'Difference of 10.0 indicates single digit OCR substitution', 'anomaly_id': 'A0004', 'affected_rows': []}

### Txn 7 - 02/05/25
Narration: PATI-PATILSHUBHAM753 UPI UPI-SHUBHAM TATYASO 7-3@OKHDFCBANK-HDFC0000222-104133825677- 02/05/25
Debit: None | Credit: 100.0 | Balance: 775686.97
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0005', 'diff': 76653.45, 'affected_rows': [], 'detail': 'Unexplained ledger drift of 76653.45'}

### Txn 8 - 02/05/25
Narration: IB BILLPAYDR-HDFCEL-457704XXXXXX6080 MB02154346030T13 02/05/25
Debit: 19071.0 | Credit: None | Balance: 756415.97
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '756.415.97', 'detail': '2 periods in numeric token — commas were read as dots'}
- debit: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '19.071.00', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 9 - 03/05/25
Narration: UPI-PMBANATWALA-STK-9665971874-1@OKBIZ AXIS-UTIB0000553-964208916371-LIFAFE 03/05/25
Debit: 48.0 | Credit: None | Balance: 776184.97
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '776.184.97', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 10 - 27/05/25
Narration: UPI-SATYAVAN RAJU SHIKHA-SHIKHARESATISH2 715@OKSBI-BKID0000503-318727385848-AUTO 000031872738584827/05/25
Debit: 125.0 | Credit: None | Balance: 698808.52
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0006', 'diff': 77081.45, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -77081.45'}

### Txn 11 - 28/05/25
Narration: ANK-HDFC0MERUPI-961239764357-POHE 28/05/25
Debit: 100.0 | Credit: None | Balance: 698708.52
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '698.708.52', 'detail': '2 periods in numeric token — commas were read as dots'}
- date: {'reason': 'DATE_NARRATION_MERGE', 'severity': 'HIGH', 'raw_text': '28/05/25UPI-YOGESHWARI-VYAPAR173204547941@HDFCB', 'date_extracted': '28/05/25', 'detail': 'Date and narration merged into single OCR token'}

### Txn 12 - 29/05/25
Narration: BHAGAT-BHARATPE.9HOROY OB0J911312@UNITYPE-UNBA000BHPE-449568036 UPI-SAMIR SHANKAR 315-PAY TO BHARATPE ME 29/05/25
Debit: 116.0 | Credit: None | Balance: 698634.42
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0007', 'diff': 1070.0, 'affected_rows': [], 'detail': 'Unexplained ledger drift of 1070.0'}

### Txn 13 - 29/05/25
Narration: Contes of this statemen will be considered correct if ao error is reported within 30 days of receipt of statemea.The address on this staemeat is that ou secord with the Bank as at the day of requestig HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement tbranch GSTN27AAACH2702HZ0 UPI-VRAJU 29/05/25
Debit: 25.0 | Credit: None | Balance: 697729.42
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '697.729.42', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 14 - 01/05/25
Narration: UPI-MRB H MOIDIN KUNHI-Q320749831@YBL YESB0YBLUPI-040656042130-WATER BOITLE 000004065604213001/05/25
Debit: 30.0 | Credit: None | Balance: 775733.61
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0008', 'diff': 78034.19, 'affected_rows': [], 'detail': 'Unexplained ledger drift of 78034.19'}

### Txn 15 - 29/05/25
Narration: POOJARY-CHAND98925134@BARODA UPI-CHANDRA MPAY-BARB0DBNMAR-771718761885-UPI 29/05/25
Debit: 10.0 | Credit: None | Balance: 697719.42
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0009', 'diff': 77857.55, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -77857.55'}

### Txn 16 - 30/05/25
Narration: UPI-MR NEHERUL ALAM.Q900083679YBL-YES BOYBLUPI-820382615256-POLISH 30/05/25
Debit: 30.0 | Credit: None | Balance: 695023.42
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0010', 'diff': 1499.0, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -1499.0'}

### Txn 17 - 03/05/25
Narration: UPI-NAIDU RAJATHI PANDI-BHARATPE.900629 O BHARATPE ME 1164@FBPE-FDRL0001382-923908372230-PAYT 000092390837223003/05/25
Debit: 500.0 | Credit: None | Balance: 775514.97
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0011', 'diff': 81321.55, 'affected_rows': [], 'detail': 'Unexplained ledger drift of 81321.55'}

### Txn 18 - 05/05/25
Narration: UPI-UJJVILAS ENTERPRISES-8999416530-2@IB L-HDFC0000222-987357529597-FOR SSL 05/05/25
Debit: 7080.0 | Credit: None | Balance: 760689.97
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '760.689.97', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 19 - 06/05/25
Narration: HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement t branchGSTN27AAACH2702HZ0 SUNIL-PAYTMQRIATOFYMQ UPI-MASTER SOURABH 06/05/25 t is that ou secord with the Bank as at the day of requesting
Debit: 7.0 | Credit: None | Balance: 760477.97
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0012', 'diff': 80.0, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -80.0'}

### Txn 20 - 09/05/25
Narration: UPI-MOHITE SUDHIR RAJARA-8826140203@PTYE S-S3IN0006491-613842042552-SENTFROMPAY TM 000061384204255209/05/25
Debit: None | Credit: 1690.0 | Balance: 754960.39
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0013', 'diff': 7207.58, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -7207.58'}

### Txn 21 - 09/05/25
Narration: UPI-HARMAN CHAHAWALA COL-GPAY-1125157392 THA 9@OKBIZAXIS-UIIB0000553-385121128725-NAS 09/05/25
Debit: 75.0 | Credit: None | Balance: 754885.39
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '754.885.39', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 22 - 10/05/25
Narration: UPI-SAGAR GOPALRAO PATIL-PAYIMQR6BMASD@P TYS-YESB0PTMUPI-182964059648-ICECREAM 10/05/25
Debit: 350.0 | Credit: None | Balance: 753867.39
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '753.867.39', 'detail': '2 periods in numeric token — commas were read as dots'}

### Txn 23 - 06/05/25
Narration: UPI-BIRBAL MEHATRE FRUIT-GPAY-1125070624 NGES 7@OKBIZAXIS-UTIB0000553-851279926996-ORA 06/05/25
Debit: 130.0 | Credit: None | Balance: 760347.97
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0014', 'diff': 24870.58, 'affected_rows': [], 'detail': 'Unexplained ledger drift of 24870.58'}

### Txn 24 - 07/05/25
Narration: LTD-YESBANKCARD BDPG@ICICI- UPI-YES BANK ICIC0DC0099-661969632254-PAY 000066196963225407/05/25
Debit: 7438.61 | Credit: None | Balance: 751982.39
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0015', 'diff': 50.0, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -50.0'}

### Txn 25 - 08/05/25
Narration: RAJU-BHARATPE9FOT7S2I9D UPI-MUJAWAR AYAJ 98-PAY TO BHARATPE ME 485150@YESBANKLTD-YESB0YESUPI-0677449611 08/05/25
Debit: 10000.0 | Credit: None | Balance: 753340.39
Suspicious Fields:
- balance: {'reason': 'POWER_OF_TEN_DRIFT', 'severity': 'HIGH', 'diff': 9900.0, 'magnitude': 4, 'detail': 'Difference of 9900.0 indicates single digit OCR substitution', 'anomaly_id': 'A0016', 'affected_rows': []}

### Txn 26 - 18/05/25
Narration: PAT-ROHAN.PATIL49@Y UPI-ROHAN SHASHIKANT BL-HDFC0000437-044449440210-MATTRESS 18/05/25
Debit: 14640.0 | Credit: None | Balance: 714022.39
Suspicious Fields:
- balance: {'reason': 'PRIMARY_BALANCE_ANOMALY', 'severity': 'HIGH', 'anomaly_id': 'A0017', 'diff': 24608.0, 'affected_rows': [], 'detail': 'Unexplained ledger drift of -24608.0'}

### Txn 27 - 22/05/25
Narration: HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds Contes of this statemen will be considered correct if ao error is reported within 30 days of receipt of statmea.The address on this stareme Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement UPI-POCKIT TECHNOLOGIES 22/05/25 t is that ou secord with the Bank as at the day of requesting
Debit: 1.0 | Credit: None | Balance: 701159.52
Suspicious Fields:
- balance: {'reason': 'MULTIPLE_DOTS', 'severity': 'HIGH', 'raw_text': '701.159.52', 'detail': '2 periods in numeric token — commas were read as dots'}

