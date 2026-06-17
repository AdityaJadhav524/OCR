import httpx
import time

def test():
    # create dummy encrypted PDF
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Bank Statement\nDate: 01-Jan-2024\nNarration: Dummy\nDebit: 100\nCredit: 200\nBalance: 300\n")
    doc.save("dummy.pdf", encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="123", owner_pw="123")
    doc.close()

    print("--- First Run ---")
    t0 = time.time()
    with open("dummy.pdf", "rb") as f:
        # First upload (gets password required and creates session)
        res1 = httpx.post("http://localhost:8000/api/process", files={"file": ("dummy.pdf", f)}, timeout=60.0)
    session_id = res1.json().get("session_id")
    
    # Unlock and process
    t0_process = time.time()
    with open("dummy.pdf", "rb") as f:
        res2 = httpx.post("http://localhost:8000/api/process", data={"password": "123", "session_id": session_id}, files={"file": ("dummy.pdf", f)}, timeout=60.0)
    t_first = time.time() - t0_process
    print(f"First unlock run took: {t_first:.3f} seconds")

    print("\n--- Second Run (Cache) ---")
    t0_cache = time.time()
    with open("dummy.pdf", "rb") as f:
        res3 = httpx.post("http://localhost:8000/api/process", data={"password": "123", "session_id": session_id}, files={"file": ("dummy.pdf", f)}, timeout=60.0)
    t_second = time.time() - t0_cache
    print(f"Second unlock run (cached) took: {t_second:.3f} seconds")

test()
