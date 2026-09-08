#!/usr/bin/env python3
"""Gabung lingga + jkt + PP101 -> CSV knowledge base final (135 kode Angga)."""
import csv, io, json, re
import html as H

KAR_KEY = re.compile(r'beracun|korosif|menyala|berbahaya|infeksius|iritasi|meledak|oksidasi|ekotoksik', re.I)

def load_lingga():
    raw = open('/tmp/lingga.html', encoding='utf-8', errors='ignore').read()
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', raw, re.S | re.I)
    out = {}
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S | re.I)
        cells = [H.unescape(re.sub(r'<[^>]+>', ' ', c)).strip() for c in cells]
        kode_idx = None
        for i, c in enumerate(cells):
            if re.fullmatch(r'[AB]\d{3}[a-z]?(?:-\d+)?', c):
                kode_idx = i
                break
        if kode_idx is None:
            continue
        code = cells[kode_idx]
        after = cells[kode_idx + 1:]
        # cari karakter
        kar_idx = None
        for i, c in enumerate(after):
            if KAR_KEY.search(c) and len(c) < 40:
                kar_idx = i
                break
        nama = ' '.join(after[:kar_idx]) if kar_idx is not None else ' '.join(after)
        nama = re.sub(r'\s+', ' ', nama).strip()
        karakter = after[kar_idx] if kar_idx is not None else ''
        kemasan = ''
        kategori = ''
        if kar_idx is not None:
            tail = after[kar_idx + 1:]
            # kategori = angka di akhir
            if tail and re.fullmatch(r'\d{1,2}', tail[-1]):
                kategori = tail[-1]
                tail = tail[:-1]
            kemasan = ' '.join(t for t in tail if t)
        out[code] = {'nama': nama, 'karakter': karakter, 'kemasan': kemasan, 'kategori': kategori}
    return out

def clean_pp101_name(nama):
    if not nama:
        return ''
    n = nama
    # header tabel nyasar -> ambil bagian setelah penanda uraian
    if 'URAIAN LIMBAH' in n:
        n = n.split('URAIAN LIMBAH')[-1]
    # buang footer tanda tangan & penanda tabel
    n = re.split(r'PRESIDEN|ttd\.|SALINAN|LAMPIRAN', n)[0]
    # potong di penanda struktural yang nyasar ke deskripsi
    n = re.split(r'[……]|KODE LIMBAH|ZAT PENCEMAR|KATEGORI BAHAYA|KODE INDUSTRI|TABEL \d|^\s*\d+\.\s*Yang|[a-g]\.\s+Yang Tidak Spesifik', n)[0]
    # buang trailing angka kategori (1/2) yg nyangkut
    n = re.sub(r'\s+[12]\s*$', '', n)
    n = re.sub(r'\s+', ' ', n).strip(' .,;:')
    return n

# override manual utk kasus header tabel / sisa kolom yang nyangkut (hasil inspeksi manual)
MANUAL_OVERRIDE = {
    'A105d': 'Limbah dan/atau buangan produk yang terkontaminasi dan/atau mengandung merkuri (Hg) dan/atau senyawanya',
    'A110d': 'Limbah karbon aktif yang mengandung zat pencemar',
    'A312-2': 'Sludge dari acid plant blowdown',
    'A337-5': 'Peralatan medis mengandung logam berat, termasuk merkuri (Hg), kadmium (Cd), dan sejenisnya',
    'B311-2': 'Sludge dari IPAL',
    'B312-5': 'Sludge IPAL',
    'B314-5': 'Sludge dari IPAL',
    'B316-5': 'Sludge dari IPAL',
    'B344-2': 'Sludge IPAL',
}

lingga = load_lingga()
jkt = json.load(open('/tmp/jkt_kodes.json'))
pp101 = json.load(open('/tmp/pp101_kodes.json'))
print("lingga:", len(lingga), "| jkt:", len(jkt), "| pp101:", len(pp101))

# baca kode Angga
src = open('/home/ubuntu/b3-chatbot/kode_limbah_b3.csv').read()
reader = csv.DictReader(io.StringIO(src))
targets = [row['kode_limbah'] for row in reader]

HEADER = ["kode_limbah", "nama_limbah", "kategori", "karakteristik",
          "sumber_limbah", "bentuk_limbah", "kemasan_angkut", "info_tambahan"]

def pick_name(code):
    if code in MANUAL_OVERRIDE:
        return MANUAL_OVERRIDE[code]
    if code in lingga and lingga[code]['nama']:
        return lingga[code]['nama']
    if code in jkt and jkt[code]:
        return re.sub(r'\s+', ' ', jkt[code]).strip()
    if code in pp101:
        return clean_pp101_name(pp101[code].get('nama', ''))
    return ''

def pick_kategori(code):
    if code in lingga and lingga[code]['kategori']:
        return lingga[code]['kategori']
    if code in pp101:
        # kategori ada di field atau di sisa nama
        kat = pp101[code].get('kategori', '')
        if kat:
            return kat
        nama = pp101[code].get('nama', '')
        m = re.search(r'\s([12])\s*$', nama)
        if m:
            return m.group(1)
    return ''

rows_out = []
no_name = []
for code in targets:
    nama = pick_name(code)
    if not nama:
        no_name.append(code)
    kat = pick_kategori(code)
    kar = lingga.get(code, {}).get('karakter', '')
    kem = lingga.get(code, {}).get('kemasan', '')
    rows_out.append({
        "kode_limbah": code, "nama_limbah": nama, "kategori": kat,
        "karakteristik": kar, "sumber_limbah": "", "bentuk_limbah": "",
        "kemasan_angkut": kem,
        "info_tambahan": f"Kategori bahaya {kat} (PP 101/2014)" if kat else "",
    })

print("total:", len(rows_out), "| tanpa nama:", len(no_name), no_name)
print("dgn karakteristik:", sum(1 for r in rows_out if r['karakteristik']))
print("dgn kategori:", sum(1 for r in rows_out if r['kategori']))

# backfill kategori: prefix A = kategori 1, B = kategori 2 (terverifikasi konsisten)
for r in rows_out:
    if not r['kategori']:
        r['kategori'] = '1' if r['kode_limbah'].startswith('A') else '2'
    if not r['info_tambahan'] and r['kategori']:
        r['info_tambahan'] = f"Kategori bahaya {r['kategori']} (PP 101/2014)"

# validasi: nama mencurigakan
suspect = []
for r in rows_out:
    n = r['nama_limbah']
    if (len(n) > 120 or re.search(r'KODE|URAIAN|INDUSTRI|KATEGORI|…|TABEL|ZAT PENCEMAR|\d{2,}', n)
            or re.search(r'\s[12]\s*$', n)):
        suspect.append((r['kode_limbah'], n))
print("\n=== NAMA MENCURIGAKAN:", len(suspect), "===")
for c, n in suspect:
    print(c, '=>', n[:140])

with open('/home/ubuntu/b3-chatbot/kode_limbah_b3.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=HEADER)
    w.writeheader()
    w.writerows(rows_out)

# sample utk review
print("\n--- SAMPLE 12 ---")
for r in rows_out[:12]:
    print(f"{r['kode_limbah']} | {r['nama_limbah'][:60]} | kat={r['kategori']} | kar={r['karakteristik']} | kem={r['kemasan_angkut']}")
print("\n--- SAMPLE dari yg sblmnya kurang ---")
for r in rows_out:
    if r['kode_limbah'] in ('A309-3', 'B344-1', 'B401', 'B417', 'A110c', 'B301-2', 'B411'):
        print(f"{r['kode_limbah']} | {r['nama_limbah'][:80]} | kat={r['kategori']}")
