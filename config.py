# ===== Konfigurasi Aplikasi =====
# Baca dari (prioritas):
#   1) Environment variable (Streamlit Cloud otomatis set dari root-level secrets)
#   2) File .env (development lokal)
#   3) st.secrets (dashboard / .streamlit/secrets.toml)
import os

from dotenv import load_dotenv

# Load .env kalau ada (development lokal). Aman: .env ke-gitignore.
load_dotenv()

def _load_streamlit_secrets_toml():
    """
    Baca .streamlit/secrets.toml manual (fallback untuk environment non-Streamlit).
    Di dalam `streamlit run`, st.secrets sudah otomatis baca file ini — fungsi ini
    cuma cadangan biar script/test biasa juga dapat nilai yang sama.
    """
    path = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
    if not os.path.exists(path):
        return {}
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib
        except ModuleNotFoundError:
            return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _get(key: str, default: str = "") -> str:
    """Prioritas: env var -> .env (sudah di load_dotenv) -> st.secrets -> secrets.toml."""
    val = os.getenv(key)
    if val:
        return val

    # st.secrets (dashboard cloud / .streamlit/secrets.toml saat streamlit run)
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    # fallback manual ke .streamlit/secrets.toml
    toml = _load_streamlit_secrets_toml()
    if key in toml:
        return str(toml[key])

    return default


# LLM API — Groq (OpenAI-compatible). Isi GROQ_API_KEY di .env / secrets dashboard.
LLM_API_KEY = _get("GROQ_API_KEY") or _get("LLM_API_KEY")
LLM_BASE_URL = _get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_MODEL = _get("DEFAULT_MODEL", "openai/gpt-oss-120b")

# PostgreSQL — WAJIB di-set via .env / secrets.
#   Lokal (VPS Docker): postgresql://user:pass@127.0.0.1:35432/b3_chatbot
#   Cloud (Supabase)  : postgresql://postgres.REF:ENC@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require
DATABASE_URL = _get("DATABASE_URL")

# Google Sheet — export CSV (sheet harus di-share "Anyone with link: Viewer")
SHEET_ID = _get("SHEET_ID", "1w3QAG-GWWHP3cg-4uIMPj41x-W3ZyiMfi3IS-JC4VbQ")
SHEET_CSV_URL = _get(
    "SHEET_CSV_URL",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv",
)

# Batas maksimum baris sheet yang dimuat ke konteks LLM
MAX_KNOWLEDGE_ROWS = int(_get("MAX_KNOWLEDGE_ROWS", "300"))

# Parameter kreatif LLM — DIKUNCI manual di sini (tidak ada slider di UI,
# karena app dipakai customer / calon customer, bukan developer).
DEFAULT_TEMPERATURE = float(_get("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_TOP_P = float(_get("DEFAULT_TOP_P", "0.9"))
DEFAULT_MAX_TOKENS = int(_get("DEFAULT_MAX_TOKENS", "1024"))


def status() -> dict:
    """Ringkasan status konfigurasi (buat panel debug di UI). Tidak pernah expose nilai asli."""
    return {
        "GROQ_API_KEY": bool(LLM_API_KEY),
        "DATABASE_URL": bool(DATABASE_URL),
        "SHEET_ID": bool(SHEET_ID),
    }
