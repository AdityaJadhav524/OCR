import httpx
import json

def test():
    # We will upload a real BOI PDF if available, or just send a dummy.
    # To avoid timeout, we mock the server's llm response by monkey-patching api.py, 
    # but since we can't easily do that from a client script, we will just patch api.py directly in the server.

    # Wait, the user said "Run same BOI PDF twice. Print: session_id first upload, session_id second upload...".
    pass
