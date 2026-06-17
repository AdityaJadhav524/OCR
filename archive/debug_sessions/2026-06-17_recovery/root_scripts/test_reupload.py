import httpx
import time

def test():
    # We will just post to /api/process using a dummy PDF
    # First, let's create a dummy encrypted PDF
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World")
    doc.save("dummy.pdf", encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="123", owner_pw="123")
    doc.close()

    print("--- 1. First upload (no password) ---")
    t0 = time.time()
    with open("dummy.pdf", "rb") as f:
        res = httpx.post("http://localhost:8000/api/process", files={"file": ("dummy.pdf", f)})
    print(res.json(), f"took {time.time()-t0:.2f}s")
    session_id = res.json().get("session_id")

    print("\n--- 2. Enter password ---")
    t0 = time.time()
    with open("dummy.pdf", "rb") as f:
        res = httpx.post("http://localhost:8000/api/process", data={"password": "123", "session_id": session_id}, files={"file": ("dummy.pdf", f)})
    print("Success:", res.json().get("success"), f"took {time.time()-t0:.2f}s")

    print("\n--- 3. Upload same PDF again (no password, BUT passing old session_id) ---")
    t0 = time.time()
    with open("dummy.pdf", "rb") as f:
        res = httpx.post("http://localhost:8000/api/process", data={"session_id": session_id}, files={"file": ("dummy.pdf", f)})
    print(res.json(), f"took {time.time()-t0:.2f}s")

test()
