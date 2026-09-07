# ===== Knowledge layer: Google Sheet kode limbah B3 =====
# Baca data dari Google Sheet (export CSV publik), parse, cache ke PostgreSQL.
import csv
import io
import re

import requests

from config import SHEET_CSV_URL, MAX_KNOWLEDGE_ROWS
from db import save_knowledge, load_knowledge


def fetch_sheet_csv(timeout: int = 20):
    """Download CSV dari Google Sheet. Return text CSV mentah."""
    resp = requests.get(SHEET_CSV_URL, timeout=timeout)
    resp.raise_for_status()
    # Google kadang balikin HTML (halaman login) kalau sheet gak publik
    if resp.text.lstrip().startswith("<"):
        raise RuntimeError("Sheet tidak bisa dibaca publik. Share dulu: Anyone with link -> Viewer.")
    return resp.text


def parse_csv_to_rows(csv_text: str):
    """CSV -> list of dict (header jadi key). Skip baris kosong total."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for r in reader:
        # buang kolom yang key-nya kosong & baris yang semua value kosong
        clean = {k.strip(): (v or "").strip() for k, v in r.items() if k and k.strip()}
        if clean and any(clean.values()):
            rows.append(clean)
    return rows


def load_sheet_rows(force_refresh: bool = False):
    """
    Ambil data limbah B3 dari Google Sheet, dengan cache di PostgreSQL.
    Kalau DB mati, tetap bisa fetch langsung dari sheet (cache di-skip).
    Return (rows, meta).
    """
    # 1) cek cache dulu (kecuali force refresh) — kalau DB error, skip cache
    if not force_refresh:
        try:
            cached = load_knowledge()
            if cached and cached["payload"].get("rows"):
                return cached["payload"]["rows"], cached["payload"].get("meta", {})
        except Exception:
            pass  # DB mati -> lanjut fetch langsung

    # 2) fetch + parse
    try:
        csv_text = fetch_sheet_csv()
    except Exception as e:
        # fallback ke cache kalau ada, biar app tetap jalan
        try:
            cached = load_knowledge()
            if cached and cached["payload"].get("rows"):
                return cached["payload"]["rows"], {**cached["payload"].get("meta", {}), "error": str(e)}
        except Exception:
            pass
        raise

    rows = parse_csv_to_rows(csv_text)
    rows = rows[:MAX_KNOWLEDGE_ROWS]
    meta = {
        "total_rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
    }
    payload = {"rows": rows, "meta": meta}
    try:
        save_knowledge(payload)
    except Exception:
        pass  # DB mati -> cache di-skip, sheet tetap kepakai
    return rows, meta


# ---------- Util buat nempelin data ke prompt LLM ----------

CODE_PATTERN = re.compile(r"\b[A-Za-z]\d{3}[a-z]?\b|\b\d{2,3}-\d{2,3}\b", re.I)


def find_code_in_query(query: str):
    """Deteksi kode limbah yang disebut user (contoh: A102d, B104d, 221-009)."""
    return CODE_PATTERN.findall(query)


def search_rows(rows, query: str):
    """
    Cari baris yang relevan dgn query:
      - cocok kode limbah persis (case-insensitive)
      - kalau gak ada kode, cocokkan kata kunci di semua kolom
    Return list baris yang match.
    """
    if not rows:
        return []

    codes = find_code_in_query(query)
    q = query.lower()

    matched = []
    for row in rows:
        haystack = " ".join(str(v).lower() for v in row.values())
        if codes and any(c.lower() in haystack for c in codes):
            matched.append(row)
        elif not codes:
            # pecah query jadi token >= 4 huruf, butuh >= 1 match
            tokens = [t for t in re.findall(r"[a-z0-9]{4,}", q)]
            if tokens and any(t in haystack for t in tokens):
                matched.append(row)
    return matched


def format_rows_for_prompt(rows, max_rows: int = 40):
    """Rows -> teks tabel (biar LLM gampang baca)."""
    if not rows:
        return "(data sheet kosong)"
    cols = list(rows[0].keys())
    header = " | ".join(cols)
    lines = [header, "-" * len(header)]
    for r in rows[:max_rows]:
        lines.append(" | ".join(str(r.get(c, "")).replace("|", "/") for c in cols))
    if len(rows) > max_rows:
        lines.append(f"... dan {len(rows) - max_rows} baris lainnya (tidak ditampilkan semua)")
    return "\n".join(lines)
