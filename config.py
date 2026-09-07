# ===== Konfigurasi Aplikasi =====
# Baca dari: 1) env var 2) file .env 3) st.secrets (Streamlit Cloud)
import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Prioritas: env var -> .env -> st.secrets (kalau jalan di Streamlit)."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


# DeepSeek API (OpenAI-compatible)
DEEPSEEK_API_KEY = _get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_MODEL = _get("DEFAULT_MODEL", "deepseek-v4-flash")

# PostgreSQL — WAJIB di-set via .env / st.secrets.
#   Lokal (VPS Docker): postgresql://user:***@127.0.0.1:35432/b3_chatbot
#   Cloud (Supabase) : postgresql://postgres.REF:***@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require
DATABASE_URL = _get("DATABASE_URL")

# Google Sheet — export CSV (sheet harus di-share "Anyone with link: Viewer")
SHEET_ID = _get("SHEET_ID", "1w3QAG-GWWHP3cg-4uIMPj41x-W3ZyiMfi3IS-JC4VbQ")
SHEET_CSV_URL = _get(
    "SHEET_CSV_URL",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv",
)

# Batas maksimum baris sheet yang dimuat ke konteks LLM
MAX_KNOWLEDGE_ROWS = int(_get("MAX_KNOWLEDGE_ROWS", "300"))
