import httpx
import time

def test():
    # create dummy encrypted PDF
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Bank Statement\nDate: 01-Jan-2024\nNarration: Dummy\nDebit: 100\nCredit: 200\nBalance: 300\n")
    doc.save("boi_dummy.pdf", encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="123", owner_pw="123")
    doc.close()

    print("=== FIRST UPLOAD ===")
    # 1. Upload without password (like dragging file to UI)
    with open("boi_dummy.pdf", "rb") as f:
        res1 = httpx.post("http://localhost:8000/api/process", files={"file": ("boi_dummy.pdf", f)}, timeout=60.0)
    data1 = res1.json()
    session_1 = data1.get("session_id")
    print(f"Upload 1 returned session_id: {session_1}")
    
    # 2. Enter password (like clicking unlock in UI)
    with open("boi_dummy.pdf", "rb") as f:
        res2 = httpx.post("http://localhost:8000/api/process", data={"password": "123", "session_id": session_1}, files={"file": ("boi_dummy.pdf", f)}, timeout=60.0)
    data2 = res2.json()
    print("Upload 1 Unlock stages:")
    for s in data2.get("stages", []):
        print(f" - {s['name']} ({s['status']})")
    
    print("\n=== SECOND UPLOAD (Same File, Same Session) ===")
    # 3. Upload again without password (Simulate App.tsx stale closure passing same session_id)
    with open("boi_dummy.pdf", "rb") as f:
        res3 = httpx.post("http://localhost:8000/api/process", data={"session_id": session_1}, files={"file": ("boi_dummy.pdf", f)}, timeout=60.0)
    data3 = res3.json()
    session_2 = data3.get("session_id")
    print(f"Upload 2 returned session_id: {session_2}")

    # 4. Enter password again
    with open("boi_dummy.pdf", "rb") as f:
        res4 = httpx.post("http://localhost:8000/api/process", data={"password": "123", "session_id": session_2}, files={"file": ("boi_dummy.pdf", f)}, timeout=60.0)
    data4 = res4.json()
    print("Upload 2 Unlock stages:")
    for s in data4.get("stages", []):
        print(f" - {s['name']} ({s['status']})")

if __name__ == "__main__":
    test()
