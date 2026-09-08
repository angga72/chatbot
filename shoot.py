#!/usr/bin/env python3
"""Screenshot chatbot Streamlit: mobile & desktop, dengan interaksi chat."""
import time
from playwright.sync_api import sync_playwright

URL = "https://chatbot-ssg.streamlit.app/~/+/"
Q = "Kode B316-5 dan A102d bisa diangkut gak kak? Terus dokumen apa aja yang harus disiapin buat pengangkutan limbah B3 dari pabrik ke tempat pengolahan?"
OUT = "/home/ubuntu/b3-chatbot/shots"

def shoot(device, viewport, prefix):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=viewport, device_scale_factor=2)
        page = ctx.new_page()
        print(f"[{prefix}] goto...")
        page.goto(URL, wait_until="domcontentloaded", timeout=180000)
        # tunggu chat input (cold start bisa lama)
        page.wait_for_selector('[data-testid="stChatInput"] textarea', timeout=180000)
        print(f"[{prefix}] app loaded, input found")
        time.sleep(3)
        # screenshot kondisi awal (header/welcome)
        header = page.locator('[data-testid="stMain"], [data-testid="main"]').first
        page.screenshot(path=f"{OUT}/{prefix}-01-awal-full.png", full_page=True)
        # kirim pesan
        ta = page.locator('[data-testid="stChatInput"] textarea')
        ta.click()
        ta.fill(Q)
        page.keyboard.press("Enter")
        print(f"[{prefix}] message sent, menunggu jawaban AI...")
        # tunggu minimal 2 chat message & reply selesai (tidak ada kursor ▌)
        page.wait_for_function(
            """() => {
                const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
                if (msgs.length < 2) return false;
                const last = msgs[msgs.length-1];
                const txt = last.textContent || '';
                return txt.length > 15 && !txt.includes('▌');
            }""",
            timeout=120000,
        )
        time.sleep(4)
        # screenshot header area
        page.screenshot(path=f"{OUT}/{prefix}-02-header.png")
        # scroll ke bawah (jawaban AI)
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        page.screenshot(path=f"{OUT}/{prefix}-03-akhir-bawah.png")
        page.screenshot(path=f"{OUT}/{prefix}-04-full.png", full_page=True)
        browser.close()
        print(f"[{prefix}] done")

if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    shoot("mobile", {"width": 390, "height": 844}, "mob")
    shoot("desktop", {"width": 1280, "height": 900}, "desk")
