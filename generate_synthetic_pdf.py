import fitz
import os

def create_synthetic_boi(filename):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4 size roughly
    
    # Header
    page.insert_text((50, 50), "BANK OF INDIA", fontsize=14)
    page.insert_text((50, 70), "Account Statement", fontsize=10)
    
    # Table Header
    y = 120
    page.insert_text((50, y), "DATE", fontsize=10)
    page.insert_text((120, y), "PARTICULARS", fontsize=10)
    page.insert_text((350, y), "DEBIT", fontsize=10)
    page.insert_text((420, y), "CREDIT", fontsize=10)
    page.insert_text((490, y), "BALANCE", fontsize=10)
    
    # Transactions
    txns = [
        ("01-Oct-2024", "OPENING BALANCE", "", "", "10000.00"),
        ("03-Oct-2024", "UPI/427719/MERCHANT", "150.00", "", "9850.00"),
        ("05-Oct-2024", "NEFT/ABC CORP/SALARY", "", "50000.00", "59850.00"),
        ("08-Oct-2024", "ATM WITHDRAWAL", "2000.00", "", "57850.00"),
        ("10-Oct-2024", "UPI/428812/GROCERY", "1200.50", "", "56649.50"),
        ("12-Oct-2024", "IMPS/XYZ/TRANSFER", "5000.00", "", "51649.50"),
        ("15-Oct-2024", "APBS CR INW - MUKHYAMANTRI MAZI LA 9284901484 AK", "", "1500.00", "53149.50"),
        ("18-Oct-2024", "POS/AMAZON/PURCHASE", "2400.00", "", "50749.50"),
        ("20-Oct-2024", "UPI/429911/BILL", "1000.00", "", "49749.50"),
        ("25-Oct-2024", "CASH DEPOSIT", "", "10000.00", "59749.50"),
        ("28-Oct-2024", "UPI/430012/RENT", "15000.00", "", "44749.50"),
    ]
    
    y += 20
    for t in txns:
        page.insert_text((50, y), t[0], fontsize=9)
        part = t[1][:35]
        page.insert_text((120, y), part, fontsize=9)
        page.insert_text((350, y), t[2], fontsize=9)
        page.insert_text((420, y), t[3], fontsize=9)
        page.insert_text((490, y), t[4], fontsize=9)

        if len(t[1]) > 35:
            y += 12
            page.insert_text((120, y), t[1][35:], fontsize=9)
        y += 20
        
    doc.save(filename)
    print(f"Created {filename}")

if __name__ == "__main__":
    create_synthetic_boi(r"z:\CA\synthetic_boi.pdf")
