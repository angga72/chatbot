# CS Bot Transporter Limbah B3

Chatbot customer service berbasis AI untuk perusahaan **transporter/jasa pengangkutan Limbah B3** (Bahan Berbahaya dan Beracun). Bot menjawab pertanyaan customer soal kode limbah B3, karakteristik, kelayakan angkut, prosedur, dan layanan — dengan **gaya bahasa santai**, **knowledge base dari Google Sheet**, dan **memory percakapan di PostgreSQL**.

Dibangun dengan Streamlit + DeepSeek LLM + Google Sheets + PostgreSQL.

---

## Arsitektur

```
┌────────────────────┐      ┌─────────────────────────┐      ┌──────────────────┐
│  Streamlit (UI)    │ ─── │  DeepSeek LLM (stream)  │ ─── │  Google Sheet    │
│  streamlit_app.py  │      │  llm.py / persona.py    │      │  (data kode B3)  │
└────────┬───────────┘      └────────────┬────────────┘      └────────┬─────────┘
         │                               │                            │
         └──────────────┬────────────────┴────────────────────────────┘
                        ▼
              ┌─────────────────────┐
              │  PostgreSQL         │  = MEMORY
              │  (Docker / Supabase)│    riwayat chat per sesi
              └─────────────────────┘
```

### Alur kerja
1. User ketik pertanyaan -> disimpan ke `chat_history` (PostgreSQL).
2. Bot **cari data relevan** di Google Sheet (cocokkan kode limbah / kata kunci).
3. Data cocok ditempel ke **system prompt** sebagai konteks.
4. **DeepSeek** generate jawaban **streaming** -> tampil + disimpan ke DB.
5. Buka sesi yang sama lagi -> riwayat dimuat dari DB (bot "ingat").

---

## Menjalankan lokal

```bash
cd b3-chatbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# isi .env (lihat .env.example)
#   DEEPSEEK_API_KEY=...   DATABASE_URL=postgresql://user:pass@host:port/dbname
#   SHEET_ID=...

streamlit run streamlit_app.py
# buka http://localhost:8501
```

Tabel database **auto-dibuat** saat app start (tidak perlu setup manual).

---

## Deploy ke Streamlit Community Cloud

1. Push repo ini ke GitHub (sudah public).
2. Buka [share.streamlit.io](https://share.streamlit.io) -> **Create app** -> pilih repo -> **Deploy**.
   - Main file: `streamlit_app.py`
3. Set **Secrets** di dashboard app (Settings -> Secrets):
   ```toml
   DEEPSEEK_API_KEY = "sk-..."
   DATABASE_URL = "postgresql://postgres.xxxx:password@aws-0-xxx.pooler.supabase.com:6543/postgres?sslmode=require"
   SHEET_ID = "1w3QAG-..."
   ```
4. App langsung jalan + memory tersimpan di Supabase.

> Penting: Google Sheet harus di-share **"Anyone with link -> Viewer"** agar bisa dibaca publik dari cloud.

---

## Database: Docker lokal atau Supabase

Aplikasi ini hanya butuh connection string PostgreSQL — bisa pakai salah satu:

| Opsi | Kapan dipakai | Cara |
|---|---|---|
| **PostgreSQL di Docker** (VPS) | Jalan lokal / di VPS sendiri | `docker run -d --name pg -e POSTGRES_PASSWORD=... -p 35432:5432 postgres:16` |
| **Supabase** (gratis) | Deploy Streamlit Cloud | Dashboard -> Settings -> Database -> **Connection string -> URI** |

Keduanya support psycopg2 langsung. Bedanya hanya `DATABASE_URL`.

---

## Google Sheet (Knowledge Base)

Bot membaca data limbah B3 dari Google Sheet (export CSV). Sheet **wajib di-share: Anyone with link -> Viewer.**

```
https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv
```

### Struktur kolom (baris 1 = header)
| kolom | contoh |
|---|---|
| `kode_limbah` | `A102d` |
| `nama_limbah` | Limbah katalis bekas |
| `kategori` | B3 dari sumber spesifik |
| `karakteristik` | Beracun |
| `sumber_limbah` | Industri kimia |
| `bentuk_limbah` | Padat / Cair / Lumpur |
| `kemasan_angkut` | Drum 200L berlabel |
| `info_tambahan` | Wajib manifest |

Kolom fleksibel — bot membaca apapun headernya. Data di-cache ke PostgreSQL (`knowledge_cache`); refresh manual lewat tombol sidebar.

---

## Parameter kreatif (sidebar app)

| Parameter | Rentang | Default | Efek |
|---|---|---|---|
| **Model** | `deepseek-v4-flash` / `deepseek-v4-pro` | flash | Pro lebih pintar, lebih lambat |
| **Persona/gaya bahasa** | Santai / Profesional / Super singkat | Santai | Karakter & tone jawaban |
| **Temperature** | 0.0 – 1.5 | 0.7 | Rendah = faktual, tinggi = kreatif |
| **Top-P** | 0.1 – 1.0 | 0.9 | Variasi pemilihan kata |
| **Max tokens** | 256 – 4096 | 1024 | Panjang maks jawaban |
| **Session ID** | auto (8 char) | — | Kunci memory di DB |

---

## Struktur file

| File | Fungsi |
|---|---|
| `streamlit_app.py` | UI Streamlit + orkestrasi (entry point) |
| `config.py` | Konfigurasi: env -> .env -> st.secrets |
| `db.py` | Layer PostgreSQL (memory, cache, feedback, auto-schema) |
| `knowledge.py` | Baca & filter data Google Sheet |
| `llm.py` | Panggil DeepSeek (streaming) + susun system prompt |
| `persona.py` | Definisi gaya bahasa bot |
| `requirements.txt` | Dependencies |
| `.env.example` | Template konfigurasi |

---

## Contoh pertanyaan

- "Kode A102d bisa diangkut gak kak?"
- "Limbah oli bekas karakteristiknya apa? aman gak diangkut?"
- "Kalau mau jemput limbah B3, dokumen apa aja yang perlu disiapin?"
- "Berapa minimum volume buat penjemputan?"
