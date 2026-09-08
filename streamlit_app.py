# ===== B3 Chatbot — Customer Service Transporter Limbah B3 =====
# Stack: Streamlit + Groq LLM (gpt-oss-120b) + Google Sheet (knowledge) + PostgreSQL (memory)
#
# Tampilan: gaya chat widget modern (header agen + status online, bubble dua arah,
# quick-reply, typing indicator, timestamp) — BEBAS EMOJI.
import base64
import os
import uuid
from datetime import datetime

import streamlit as st

from config import DEFAULT_MODEL, status as config_status
from db import save_message, load_history, clear_history, get_all_sessions, save_feedback, ensure_schema
from knowledge import load_sheet_rows, search_rows, format_rows_for_prompt
from llm import stream_chat, build_system_prompt
from persona import PERSONAS

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Bima — CS Limbah B3",
    page_icon="assets/avatar-bot.png",
    layout="centered",
)

# ---------------- Konstanta UI ----------------
BOT_AVATAR = "assets/avatar-bot.png"
USER_AVATAR = "assets/avatar-user.png"


def _asset_b64(name: str) -> str:
    """Baca gambar asset -> data URI (buat header HTML)."""
    try:
        with open(os.path.join("assets", name), "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""


HEADER_AVATAR = _asset_b64("avatar-bot.png")

# ---------------- Custom CSS ----------------
CSS = """
<style>
/* ===== dasar ===== */
.stApp { font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif; }
[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(180deg, #EDF2EE 0%, #F5F7F5 140px, #F8FAF8 100%);
}
.block-container { padding-top: 1.1rem; padding-bottom: 6.5rem; max-width: 900px; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* ===== header agen ===== */
.chat-header {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    background: #FFFFFF; border: 1px solid #E1E7E3; border-radius: 18px;
    padding: 12px 18px; box-shadow: 0 1px 4px rgba(16,24,40,.06);
}
.chat-h-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
.chat-h-avatar { width: 46px; height: 46px; border-radius: 50%; object-fit: cover;
    box-shadow: 0 0 0 2px #fff, 0 0 0 4px rgba(20,83,45,.18); }
.chat-h-name { font-size: 17px; font-weight: 800; color: #14532D; line-height: 1.2; }
.chat-h-role { font-size: 12.5px; color: #5B6B62; line-height: 1.35; }
.chat-h-right { flex-shrink: 0; text-align: right; }
.chat-h-status { display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px;
    font-weight: 700; color: #166534; background: #EDF7F0; border: 1px solid #CDE8D5;
    border-radius: 999px; padding: 4px 11px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #22C55E; display: inline-block;
    animation: pulse 1.8s infinite; }
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(34,197,94,.45); }
    70% { box-shadow: 0 0 0 6px rgba(34,197,94,0); }
    100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
}
.chat-h-resp { font-size: 11px; color: #8A9A90; margin-top: 3px; }

/* ===== kartu sambutan ===== */
.welcome-card { background: #FFFFFF; border: 1px solid #E1E7E3; border-radius: 18px;
    padding: 20px 24px 16px; margin: 10px 0 4px; box-shadow: 0 1px 4px rgba(16,24,40,.05); }
.welcome-title { font-size: 19px; font-weight: 800; color: #14532D; margin-bottom: 6px; }
.welcome-sub { font-size: 14px; color: #4B5A52; line-height: 1.65; }
.welcome-list { margin: 8px 0 2px; padding: 0; list-style: none; }
.welcome-list li { font-size: 13.5px; color: #3F4D46; padding: 3px 0 3px 22px; position: relative; }
.welcome-list li::before { content: ""; position: absolute; left: 4px; top: 9px; width: 8px; height: 8px;
    border-radius: 50%; background: #14532D; }
.welcome-hint { font-size: 12.5px; color: #7C8B83; margin-top: 10px; }

/* ===== chip quick reply (tombol pill) ===== */
div.stButton > button[kind="secondary"] {
    border-radius: 999px !important; border: 1px solid #C9E0D1 !important;
    background: #F1F7F3 !important; color: #14532D !important;
    font-weight: 600 !important; font-size: 13.5px !important;
    padding: 6px 14px !important; transition: all .15s ease;
}
div.stButton > button[kind="secondary"]:hover {
    background: #14532D !important; color: #fff !important; border-color: #14532D !important;
}
.chip-label { font-size: 12px; color: #8A9A90; text-align: center; margin: 2px 0 8px; }

/* ===== bubble chat ===== */
[data-testid="stChatMessage"] {
    display: flex; gap: 10px; align-items: flex-end; margin: 10px 0;
}
[data-testid="stChatMessageAvatar"] img {
    width: 34px; height: 34px; border-radius: 50%; object-fit: cover;
    box-shadow: 0 0 0 1px #E3E8E5;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
    background: #FFFFFF; border: 1px solid #E3E8E5; border-radius: 16px 16px 16px 4px;
    padding: 9px 14px; max-width: 76%; box-shadow: 0 1px 2px rgba(16,24,40,.04);
    color: #1F2937; font-size: 15px; line-height: 1.55;
}
[data-testid="stChatMessageContent"] p { margin-bottom: .4em; }
[data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0; }

/* bubble user -> hijau, rata kanan */
[data-testid="stChatMessage"]:has(img[alt="user avatar"]) { flex-direction: row-reverse; }
[data-testid="stChatMessage"]:has(img[alt="user avatar"]) [data-testid="stChatMessageContent"] {
    background: #14532D; border-color: #14532D; color: #FFFFFF;
    border-radius: 16px 16px 4px 16px;
}
[data-testid="stChatMessage"]:has(img[alt="user avatar"]) [data-testid="stChatMessageContent"] p { color: #FFFFFF; }

/* timestamp di dalam bubble
   FIX kepotong: layout st.caption Streamlit collapse (~6px) padahal teks render ~17px,
   akibatnya jam nembus keluar batas bawah bubble. Paksa tinggi asli biar bubble nutupin. */
[data-testid="stChatMessageContent"] [data-testid="stMarkdown"]:has([data-testid="stCaptionContainer"]) {
    height: auto !important; min-height: 17px !important;
}
[data-testid="stChatMessageContent"] [data-testid="stVerticalBlock"]:has([data-testid="stCaptionContainer"]) {
    height: auto !important;
}
[data-testid="stChatMessageContent"] [data-testid="stCaptionContainer"] {
    display: block !important; height: auto !important; min-height: 16px !important;
    line-height: 1.4 !important; margin: 4px 0 0 0 !important;
    color: #9AA7A0; font-size: 11px;
}
[data-testid="stChatMessage"]:has(img[alt="user avatar"]) [data-testid="stChatMessageContent"] [data-testid="stCaptionContainer"] {
    color: rgba(255,255,255,.7);
}

/* ===== typing indicator ===== */
.typing { display: flex; align-items: center; gap: 5px; padding: 4px 2px; }
.typing span { width: 7px; height: 7px; border-radius: 50%; background: #9DB8A8;
    display: inline-block; animation: blink 1.4s infinite both; }
.typing span:nth-child(2) { animation-delay: .2s; }
.typing span:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%,80%,100% { opacity: .25; transform: scale(.9); } 40% { opacity: 1; transform: scale(1); } }

/* ===== chat input ===== */
[data-testid="stChatInput"] {
    border: 1px solid #D6DED9; border-radius: 26px; background: #FFFFFF;
    box-shadow: 0 2px 12px rgba(16,24,40,.07);
}
[data-testid="stChatInput"]:focus-within { border-color: #14532D;
    box-shadow: 0 0 0 3px rgba(20,83,45,.14); }
[data-testid="stChatInput"] textarea { font-size: 15px; }
[data-testid="stChatInput"] button {
    background-color: #14532D !important; border-radius: 50% !important;
}
[data-testid="stChatInput"] button:hover { background-color: #1D6B3E !important; }

/* ===== feedback kecil ===== */
div.stButton.fb-kecil > button[kind="secondary"] {
    border-radius: 999px !important; border: 1px solid #E0E7E3 !important;
    background: #FFFFFF !important; color: #5B6B62 !important;
    font-size: 12.5px !important; font-weight: 600 !important; padding: 3px 14px !important;
    box-shadow: none !important;
}
div.stButton.fb-kecil > button[kind="secondary"]:hover {
    border-color: #14532D !important; color: #14532D !important; background: #F1F7F3 !important;
}

/* ===== sidebar ringan ===== */
[data-testid="stSidebar"] { background: #FAFBF9; }
[data-testid="stSidebar"] hr { border-color: #E5EAE7; }
</style>
"""

# ---------------- Init session state ----------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sheet_rows" not in st.session_state:
    st.session_state.sheet_rows = None
if "sheet_meta" not in st.session_state:
    st.session_state.sheet_meta = {}
if "db_ok" not in st.session_state:
    st.session_state.db_ok = None
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = True
if "feedback_done" not in st.session_state:
    st.session_state.feedback_done = False

# ---------------- Cek koneksi database (sekali per session) ----------------
if st.session_state.db_ok is None:
    try:
        ensure_schema()
        st.session_state.db_ok = True
    except Exception as e:
        st.session_state.db_ok = False
        st.session_state.db_error = str(e)

DB_OK = st.session_state.db_ok


def db_save(role: str, content: str):
    if DB_OK:
        try:
            save_message(st.session_state.session_id, role, content)
        except Exception:
            pass


def db_history():
    if DB_OK:
        try:
            return load_history(st.session_state.session_id, limit=30)
        except Exception:
            return []
    return []


def db_clear():
    if DB_OK:
        try:
            clear_history(st.session_state.session_id)
        except Exception:
            pass


def db_sessions():
    if DB_OK:
        try:
            return get_all_sessions()
        except Exception:
            return []
    return []


def now_ts() -> str:
    return datetime.now().strftime("%H:%M")


# ---------------- Muat knowledge (Google Sheet) ----------------
def get_sheet_data():
    if st.session_state.sheet_rows is None:
        try:
            rows, meta = load_sheet_rows()
            st.session_state.sheet_rows = rows
            st.session_state.sheet_meta = meta
        except Exception as e:
            st.session_state.sheet_rows = []
            st.session_state.sheet_meta = {"error": str(e)}
    return st.session_state.sheet_rows, st.session_state.sheet_meta


rows, meta = get_sheet_data()

# ---------------- Muat history dari PostgreSQL (memory) ----------------
if not st.session_state.messages:
    for msg in db_history():
        st.session_state.messages.append(
            {"role": msg["role"], "content": msg["content"], "ts": ""}
        )

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### Konfigurasi")

    st.caption(f"Model: {DEFAULT_MODEL}")
    persona_name = st.selectbox(
        "Persona / gaya bahasa", list(PERSONAS.keys()), index=0
    )
    temperature = st.slider(
        "Temperature (kreativitas)", 0.0, 1.5, 0.7, 0.1,
        help="Rendah = faktual/kaku. Tinggi = kreatif/liar.",
    )
    top_p = st.slider("Top-P (variasi kata)", 0.1, 1.0, 0.9, 0.05)
    max_tokens = st.slider("Max token jawaban", 256, 4096, 1024, 128)

    st.divider()
    st.markdown("#### Memory (PostgreSQL)")
    if not DB_OK:
        st.warning("Database tidak tersambung. Memory hanya bertahan selama sesi ini.")
    st.caption(f"Session ID: `{st.session_state.session_id}`")
    if st.button("Sesi baru", width="stretch"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages = []
        st.session_state.feedback_given = True
        st.rerun()
    if st.button("Hapus riwayat sesi ini", width="stretch"):
        db_clear()
        st.session_state.messages = []
        st.session_state.feedback_given = True
        st.rerun()

    sessions = db_sessions()
    if sessions:
        with st.expander(f"Tersimpan di DB ({len(sessions)} sesi)"):
            for s in sessions[:10]:
                st.write(
                    f"`{s['session_id']}` — {s['n']} pesan"
                    f" · {s['last_seen']:%d/%m %H:%M}"
                )

    st.divider()
    st.markdown("#### Status data")
    if st.button("Muat ulang data sheet", width="stretch"):
        st.session_state.sheet_rows = None
        st.rerun()
    with st.expander("Status knowledge base (Google Sheet)"):
        if meta.get("error"):
            st.warning(f"Sheet gagal dibaca: {meta['error']}")
        st.write(f"**Total baris data:** {meta.get('total_rows', len(rows))}")
        if meta.get("columns"):
            st.write(f"**Kolom:** {', '.join(meta['columns'])}")
        if rows:
            st.dataframe(rows[:20], width="stretch", hide_index=True)
        else:
            st.info("Sheet masih kosong atau belum diisi.")

    with st.expander("Status konfigurasi"):
        cfg = config_status()
        for key, ok in cfg.items():
            label = "terisi" if ok else "KOSONG"
            st.write(f"- {key}: {label}")
        if not cfg.get("DATABASE_URL"):
            st.markdown(
                "**Cara set secrets (Cloud):** Settings -> Secrets, paste isi "
                "`.streamlit/secrets.toml`. Semua key root-level (tanpa `[section]`)."
            )
        if not cfg.get("GROQ_API_KEY"):
            st.markdown("Isi `GROQ_API_KEY` di secrets dashboard.")

# ---------------- Render CSS + header ----------------
st.markdown(CSS, unsafe_allow_html=True)

header_html = f"""
<div class="chat-header">
  <div class="chat-h-left">
    <img class="chat-h-avatar" src="{HEADER_AVATAR}" alt="Bima">
    <div>
      <div class="chat-h-name">Bima</div>
      <div class="chat-h-role">Customer Service · Transporter Limbah B3</div>
    </div>
  </div>
  <div class="chat-h-right">
    <span class="chat-h-status"><span class="dot"></span>Online</span>
    <div class="chat-h-resp">Bales cepat, jam kerja 08.00–17.00 WIB</div>
  </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

QUICK_REPLIES = [
    ("Cek kode limbah", "Kode A102d bisa diangkut gak kak?"),
    ("Layanan angkut", "Layanan pengangkutan limbah B3 itu gimana kak?"),
    ("Dokumen angkutan", "Dokumen apa aja yang dibutuhkan buat pengangkutan?"),
    ("Minta penawaran", "Gua mau minta penawaran harga buat angkut limbah."),
]

show_welcome = len(st.session_state.messages) == 0 and "pending_prompt" not in st.session_state

if show_welcome:
    welcome_html = """
<div class="welcome-card">
  <div class="welcome-title">Halo kak, gua Bima.</div>
  <div class="welcome-sub">
    CS dari perusahaan jasa transportasi &amp; pengangkutan limbah B3 berizin resmi.
    Di sini kakak bisa:
  </div>
  <ul class="welcome-list">
    <li>Cek apakah kode limbah B3 bisa diangkut sama kita</li>
    <li>Tanya layanan pengangkutan, armada, dan jadwal</li>
    <li>Tanya dokumen angkutan (manifest, PLB3) dan prosedurnya</li>
  </ul>
  <div class="welcome-hint">Langsung tanya aja di kolom chat, atau pilih topik di bawah:</div>
</div>
"""
    st.markdown(welcome_html, unsafe_allow_html=True)
    cols = st.columns(len(QUICK_REPLIES))
    for col, (label, q) in zip(cols, QUICK_REPLIES):
        if col.button(label, key=f"qr_{label}", width="stretch"):
            st.session_state.pending_prompt = q
            st.rerun()
    st.caption("Tip: kirim kode limbah (misal A102d) biar dicek ke daftar layanan.")

# ---------------- Render riwayat chat ----------------
for msg in st.session_state.messages:
    role = msg["role"]
    avatar = BOT_AVATAR if role == "assistant" else USER_AVATAR
    with st.chat_message(role, avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("ts"):
            st.caption(msg["ts"])

# ---------------- Disclaimer ----------------
st.caption(
    "Dibalas otomatis oleh asisten AI. Untuk penawaran harga dan info teknis final, "
    "tim operasional kami siap bantu lewat kontak resmi."
)

# ---------------- Chat input ----------------
prompt = st.chat_input("Contoh: 'Kode A102d bisa diangkut gak kak?'")

incoming = prompt or st.session_state.pop("pending_prompt", None)

if incoming:
    # 1) tampilkan + simpan pesan user
    ts = now_ts()
    st.session_state.messages.append({"role": "user", "content": incoming, "ts": ts})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(incoming)
        st.caption(ts)
    db_save("user", incoming)

    # 2) cari data sheet yang relevan
    matched = search_rows(rows, incoming)
    if matched:
        context = format_rows_for_prompt(matched, max_rows=20)
    elif rows:
        context = format_rows_for_prompt(rows[:10], max_rows=10)
    else:
        context = ""

    # 3) bangun prompt
    system_prompt = build_system_prompt(PERSONAS[persona_name], sheet_context=context)
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages[-10:]:
        api_messages.append({"role": m["role"], "content": m["content"]})

    # 4) stream jawaban (dengan typing indicator)
    typing_html = '<div class="typing"><span></span><span></span><span></span></div>'
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        placeholder = st.empty()
        buffer = ""
        try:
            placeholder.markdown(typing_html, unsafe_allow_html=True)
            gen = stream_chat(
                api_messages,
                model=DEFAULT_MODEL,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            for piece in gen:
                buffer += piece
                placeholder.markdown(buffer + "▌")
            placeholder.markdown(buffer)
        except Exception as e:
            buffer = f"Gagal hubungi model: {e}. Cek API key / koneksi."
            placeholder.markdown(buffer)

    # 5) simpan jawaban assistant
    ts = now_ts()
    st.session_state.messages.append({"role": "assistant", "content": buffer, "ts": ts})
    db_save("assistant", buffer)
    st.session_state.feedback_given = False
    st.session_state.feedback_done = False

# ---------------- Feedback (di bawah jawaban terakhir) ----------------
if (
    len(st.session_state.messages) >= 2
    and st.session_state.messages[-1]["role"] == "assistant"
):
    if not st.session_state.feedback_given:
        last_q = next(
            (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
            "",
        )
        fb1, fb2 = st.columns(2)
        with fb1:
            if st.button("Bantuan membantu", key="fb_pos"):
                save_feedback(st.session_state.session_id, last_q, "positif")
                st.session_state.feedback_given = True
                st.session_state.feedback_done = True
                st.rerun()
        with fb2:
            if st.button("Kurang tepat", key="fb_neg"):
                save_feedback(st.session_state.session_id, last_q, "negatif")
                st.session_state.feedback_given = True
                st.session_state.feedback_done = True
                st.rerun()
    elif st.session_state.feedback_done:
        st.caption("Makasih kak, masukannya udah gua catat buat evaluasi tim.")
