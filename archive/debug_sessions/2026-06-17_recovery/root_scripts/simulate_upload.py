import httpx
import time
import json
import os

API_URL = "http://localhost:8000"
PDF_PATH = r"Z:\CA\validation_lab\backend\temp\11707454011-JUL-25221947 2.PDF" # Let me check if this exists

def main():
    if not os.path.exists(PDF_PATH):
        # We'll use any Bank of India pdf if we can find it
        # Actually I can just use the debug endpoint if I want, or simulate the API.
        pass
    
    # Let's just upload a file
    with open(PDF_PATH, "rb") as f:
        files = {"file": ("11707454011-JUL-25221947 2.PDF", f, "application/pdf")}
        resp = httpx.post(f"{API_URL}/api/upload", files=files, timeout=30.0)
        
    data = resp.json()
    session_id = data["session_id"]
    print(f"Uploaded. Session ID: {session_id}")
    
    # Poll until extraction is done
    for _ in range(30):
        time.sleep(2)
        resp = httpx.get(f"{API_URL}/api/session/{session_id}", timeout=10.0)
        session_data = resp.json()
        
        # Check if normalization is done
        stages = session_data.get("stages", [])
        norm_stage = next((s for s in stages if s["name"] == "Normalization"), None)
        
        if norm_stage and norm_stage["status"] in ["SUCCESS", "ERROR"]:
            break
            
    print("\n=== 4. API RESPONSE PAYLOAD (final_transactions) ===")
    final_txns = session_data.get("final_transactions", [])
    print(json.dumps(final_txns[:5], indent=2))
    
    # Now hit my new debug cache endpoint!
    cache_resp = httpx.get(f"{API_URL}/api/debug/cache")
    if cache_resp.status_code == 200:
        session_cache = cache_resp.json().get(session_id, {})
        print("\n=== 5. SESSION_CACHE OBJECT (transactions) ===")
        print(json.dumps(session_cache.get("transactions", [])[:5], indent=2))
        
        print("\n=== 2. NORMALIZATION INPUT (llm_result.transactions) ===")
        llm_res = session_cache.get("llm_result", {})
        print(json.dumps(llm_res.get("transactions", [])[:5], indent=2))
        
    print("\n=== 6. EXACT JSON RECEIVED BY REACT FRONTEND ===")
    print(json.dumps(final_txns[:5], indent=2))

if __name__ == "__main__":
    main()
