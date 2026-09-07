# ===== B3 Chatbot — Customer Service Transporter Limbah B3 =====
# Stack: Streamlit + DeepSeek LLM + Google Sheet (knowledge) + PostgreSQL (memory)
#
# Jalankan:  streamlit run streamlit_app.py
import os
import uuid

import streamlit as st

from config import DEFAULT_MODEL
from db import save_message, load_history, clear_history, get_all_sessions, save_feedback, ensure_schema
from knowledge import load_sheet_rows, search_rows, format_rows_for_prompt
from llm import stream_chat, build_system_prompt
from persona import PERSONAS

# ---------------- Page config ----------------
st.set_page_config(page_title="CS Bot Limbah B3", layout="centered")

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
    st.session_state.db_ok = None  # None = belum dicek, True/False = hasil cek

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
    """Simpan ke DB kalau tersedia; kalau enggak, diam (memory sesi tetap jalan)."""
    if DB_OK:
        try:
            save_message(st.session_state.session_id, role, content)
        except Exception:
            pass


def db_history():
    """Ambil riwayat dari DB kalau tersedia."""
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


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Konfigurasi")

    model = st.selectbox(
        "Model LLM",
        ["deepseek-v4-flash", "deepseek-v4-pro"],
        index=0,
        help="Flash = cepat dan hemat. Pro = lebih pintar, lebih lambat.",
    )
    persona_name = st.selectbox(
        "Persona / gaya bahasa", list(PERSONAS.keys()), index=0
    )
    temperature = st.slider("Temperature (kreativitas)", 0.0, 1.5, 0.7, 0.1,
                            help="Rendah = faktual/kaku. Tinggi = kreatif/liar.")
    top_p = st.slider("Top-P (variasi kata)", 0.1, 1.0, 0.9, 0.05)
    max_tokens = st.slider("Max token jawaban", 256, 4096, 1024, 128)

    st.divider()
    st.subheader("Memory (PostgreSQL)")
    if not DB_OK:
        st.warning("Database tidak tersambung. Memory hanya bertahan selama sesi ini.")
    st.caption(f"Session ID: `{st.session_state.session_id}`")
    if st.button("Sesi baru", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages = []
        st.rerun()
    if st.button("Hapus riwayat sesi ini", use_container_width=True):
        db_clear()
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Status data")
    if st.button("Muat ulang data sheet", use_container_width=True):
        st.session_state.sheet_rows = None  # paksa refresh
        st.rerun()

# ---------------- Muat knowledge (Google Sheet) ----------------
def get_sheet_data():
    """Load data sheet (cache di session). Error ditangkap supaya chat tetap jalan."""
    if st.session_state.sheet_rows is None:
        try:
            rows, meta = load_sheet_rows()
            st.session_state.sheet_rows = rows
            st.session_state.sheet_meta = meta
        except Exception as e:
            st.session_state.sheet_rows = []  # kosong, bukan error fatal
            st.session_state.sheet_meta = {"error": str(e)}
    return st.session_state.sheet_rows, st.session_state.sheet_meta

rows, meta = get_sheet_data()

# ---------------- Muat history dari PostgreSQL (memory) ----------------
if not st.session_state.messages:
    for msg in db_history():
        st.session_state.messages.append(
            {"role": msg["role"], "content": msg["content"]}
        )

# ---------------- Render header + info data ----------------
st.title("CS Bot Transporter Limbah B3")
st.caption("Tanya soal kode limbah B3, layanan angkut, atau dokumen. Data dari Google Sheet + memory PostgreSQL.")

with st.expander("Status knowledge base (Google Sheet)"):
    if meta.get("error"):
        st.warning(f"Sheet gagal dibaca: {meta['error']}")
    st.write(f"**Total baris data:** {meta.get('total_rows', len(rows))}")
    if meta.get("columns"):
        st.write(f"**Kolom:** {', '.join(meta['columns'])}")
    if rows:
        st.dataframe(rows[:20], use_container_width=True, hide_index=True)
    else:
        st.info("Sheet masih kosong atau belum diisi. Bot tetap bisa jawab pertanyaan umum layanan.")

sessions = db_sessions()
if sessions:
    with st.expander(f"Memory di PostgreSQL ({len(sessions)} sesi tersimpan)"):
        for s in sessions[:10]:
            st.write(f"`{s['session_id']}` — {s['n']} pesan · terakhir {s['last_seen']:%Y-%m-%d %H:%M}")

# ---------------- Render chat history ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- Chat input & response ----------------
if prompt := st.chat_input("Contoh: 'Kode A102d bisa diangkut gak kak?'"):
    # 1) tampilkan + simpan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    db_save("user", prompt)

    # 2) cari data sheet yang relevan
    matched = search_rows(rows, prompt)
    if matched:
        context = format_rows_for_prompt(matched, max_rows=20)
    elif rows:
        # gak ada match spesifik -> kasih cuplikan umum biar bot tau isi datanya
        context = format_rows_for_prompt(rows[:10], max_rows=10)
    else:
        context = ""

    # 3) bangun prompt
    system_prompt = build_system_prompt(
        PERSONAS[persona_name], sheet_context=context
    )
    api_messages = [{"role": "system", "content": system_prompt}]
    # kirim 10 pesan terakhir sbg konteks (hemat token, cukup buat inget konteks)
    for m in st.session_state.messages[-10:]:
        api_messages.append({"role": m["role"], "content": m["content"]})

    # 4) stream jawaban
    with st.chat_message("assistant"):
        placeholder = st.empty()
        buffer = ""
        try:
            gen = stream_chat(
                api_messages,
                model=model,
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
    st.session_state.messages.append({"role": "assistant", "content": buffer})
    db_save("assistant", buffer)
    st.session_state.feedback_given = False  # reset feedback utk turn baru

# ---------------- Feedback (render setiap run, di luar blok input) ----------------
if (
    len(st.session_state.messages) >= 2
    and st.session_state.messages[-1]["role"] == "assistant"
    and not st.session_state.get("feedback_given", False)
):
    last_q = next(
        (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
        "",
    )
    col1, col2 = st.columns(2)
    if col1.button("Bantuan membantu", use_container_width=True):
        save_feedback(st.session_state.session_id, last_q, "positif")
        st.session_state.feedback_given = True
        st.toast("Terima kasih atas masukannya.")
        st.rerun()
    if col2.button("Kurang tepat", use_container_width=True):
        save_feedback(st.session_state.session_id, last_q, "negatif")
        st.session_state.feedback_given = True
        st.toast("Siap, masukan diteruskan ke tim.")
        st.rerun()
