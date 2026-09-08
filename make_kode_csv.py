#!/usr/bin/env python3
"""Buat CSV knowledge base kode limbah B3 dari daftar Angga (kolom detail kosong)."""
import csv

CODES_RAW = """A101d A102d A103d A104d A105d A106d A107d A108d A109c A109d A110c A110d A111d
A304-3 A305-2 A306-2 A307-1 A307-2 A309-3 A309-4 A310-1 A310-3 A312-1 A312-2 A313-3
A317-1 A317-2 A317-3 A318-1 A318-2 A323-1 A323-2 A323-3 A324-2 A324-3 A324-6 A324-7
A324-8 A325-1 A327-1 A337-1 A337-2 A337-3 A337-4 A337-5 A338-1 A338-2 A338-3 A339-1
A341-1 A345-1 A345-2 A346-1 A347-1 A347-2 A352-1 A352-2
B102d B104d B105d B106d B107d B108d B109d B110d
B301-1 B301-2 B301-3 B301-6 B301-7 B304-1 B305-1 B305-5 B306-1 B306-4 B307-1 B309-1
B309-3 B310-1 B311-2 B312-5 B313-2 B313-3 B313-5 B313-6 B313-7 B313-8 B314-1 B314-3
B314-5 B316-4 B316-5 B317-3 B321-1 B321-3 B321-4 B321-7 B322-2 B322-3 B323-1 B323-2
B323-3 B323-4 B323-5 B324-1 B328-3 B328-4 B328-6 B339-2 B344-1 B344-2 B345-1 B347-1
B347-2 B347-3 B351-3 B351-4 B353-1 B354-2 B354-3 B355-2
B401 B402 B405 B407 B409 B410 B411 B413 B415 B417
A108c B322-1 A322-3 B324-3"""

codes = CODES_RAW.split()
# dedup sambil pertahankan urutan
seen = set()
uniq = []
for c in codes:
    if c not in seen:
        seen.add(c)
        uniq.append(c)

HEADER = [
    "kode_limbah", "nama_limbah", "kategori", "karakteristik",
    "sumber_limbah", "bentuk_limbah", "kemasan_angkut", "info_tambahan",
]

with open("kode_limbah_b3.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    for c in uniq:
        w.writerow([c, "", "", "", "", "", "", ""])

print("total mentah:", len(codes))
print("duplikat dibuang:", len(codes) - len(uniq))
print("total unik:", len(uniq))
# kelompok
from collections import Counter
groups = Counter()
for c in uniq:
    if c.startswith("A1"): groups["A1xx (sumber tidak spesifik?)"] += 1
    elif c.startswith("A3"): groups["A3xx"] += 1
    elif c.startswith("B1"): groups["B1xx"] += 1
    elif c.startswith("B3"): groups["B3xx"] += 1
    elif c.startswith("B4"): groups["B4xx"] += 1
    else: groups["lain"] += 1
for g, n in groups.most_common():
    print(f"  {g}: {n}")
