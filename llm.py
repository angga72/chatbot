# ===== LLM layer: Groq (OpenAI-compatible) — model gpt-oss-120b =====
import json

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


def stream_chat(
    messages,
    model: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 1024,
    extra_system: str = "",
):
    """
    Panggil DeepSeek dgn streaming. `messages` = list [{role, content}].
    Generator: yield string per chunk.
    Di akhir yield, yield None? — TIDAK, lebih baik return penuh dari luar.
    """
    client = get_client()
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=True,
    )
    full = []
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            piece = chunk.choices[0].delta.content
            full.append(piece)
            yield piece
    return "".join(full)


def build_system_prompt(persona: str, sheet_context: str = "", extra: str = "") -> str:
    """
    Susun system prompt dari persona + konteks sheet.
    `persona` berisi instruksi karakter/gaya.
    `sheet_context` = data limbah B3 (sudah diformat).
    """
    parts = [persona.strip()]
    if sheet_context.strip():
        parts.append(
            "\n\n=== DATA KODE LIMBAH B3 (dari Google Sheet internal, sumber resmi) ===\n"
            + sheet_context
            + "\n=== AKHIR DATA ===\n\n"
            "Gunakan data di atas sebagai sumber UTAMA kalau customer nanya soal kode limbah, "
            "karakteristik, atau kelayakan angkut. Kalau kode yang ditanyakan TIDAK ada di data, "
            "bilang jujur kalau belum ada di daftar layanan dan sarankan hubungi tim operasional — "
            "JANGAN mengarang karakteristik dari luar data."
        )
    if extra.strip():
        parts.append("\nInstruksi tambahan sesi ini:\n" + extra.strip())
    return "\n".join(parts)
