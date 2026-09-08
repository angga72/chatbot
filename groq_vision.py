#!/usr/bin/env python3
"""Analisis screenshot pake Groq vision (Llama-4) via openai SDK."""
import base64, os, sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("/home/ubuntu/b3-chatbot/.env")
KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(api_key=KEY, base_url="https://api.groq.com/openai/v1")

try:
    ids = sorted(m.id for m in client.models.list().data)
    print("MODEL TERSEDIA:", ids)
    vision = [i for i in ids if any(k in i.lower() for k in ("llama-4", "llava", "maverick", "scout", "omni", "vision"))]
    print("KANDIDAT VISION:", vision)
    if not vision:
        sys.exit("tidak ada model vision")
except Exception as e:
    print("GAGAL list models:", type(e).__name__, e)
    # fallback: tebak model vision populer
    vision = ["meta-llama/llama-4-maverick", "meta-llama/llama-4-scout-17b-16e-instruct"]

IMG = "/home/ubuntu/hermes-prod/data/image_cache/img_553689f74316.jpg"
if not os.path.exists(IMG):
    IMG = "/opt/data/image_cache/img_553689f74316.jpg"
b64 = base64.b64encode(open(IMG, "rb").read()).decode()

PROMPT = """Analisis screenshot aplikasi chat mobile ini secara detail (Bahasa Indonesia):
1. Bagian ATAS: elemen header/profile "Bima" (avatar bulat, nama Bima, status Online, teks jam kerja 08.00-17.00 WIB) — apakah ada yang terpotong/clipped? Sebut elemen & sisi potongnya, perkirakan berapa banyak teks yang hilang.
2. Bagian chat/bubble: apakah teks jawaban AI terpotong di dalam bubble? Bubble mana (user hijau / bot putih), di posisi mana (atas/bawah/kanan/kiri), teks apa yang kelihatan hilang?
3. Masalah visual lain: tumpang tindih, elemen melebar keluar layar, jarak aneh, header kelewat tinggi/pendek, scroll ganda.
4. Perkiraan orientasi (HP sempit / tablet / desktop) dan warna dominan.
Jawab poin per poin, padat, apa adanya."""

for model in vision:
    try:
        print(f"\n>>> Coba model: {model}")
        resp = client.chat.completions.create(
            model=model, temperature=0.2, max_tokens=1500,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
        )
        print("===== ANALISIS =====")
        print(resp.choices[0].message.content)
        break
    except Exception as e:
        print("GAGAL:", type(e).__name__, str(e)[:300])
