# core/config.py
# Environment variable loader — LLM keys only.
# No Supabase. No database. No auth.

import os
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

# ── Gemini (document classification + transaction extraction) ─────────────────
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY")
CLASSIFIER_MODEL = os.environ.get("CLASSIFIER_MODEL", "models/gemini-2.5-flash")
LLM_PARSER_MODEL = os.environ.get("LLM_PARSER_MODEL", "models/gemini-2.5-flash")

# ── OpenRouter fallback ───────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"

# ── 9router fallback ──────────────────────────────────────────────────────────
NINEROUTER_API_KEY = os.environ.get("NINEROUTER_API_KEY")
NINEROUTER_MODEL   = os.environ.get("NINEROUTER_MODEL", "anthropic/claude-sonnet-4.5")
NINEROUTER_URL     = os.environ.get("NINEROUTER_URL", "https://api.9router.com/v1/chat/completions")

# ── LLM provider priority (gemini | openrouter | 9router) ────────────────────
CODE_GEN_PROVIDER = os.environ.get("CODE_GEN_PROVIDER", "gemini")
