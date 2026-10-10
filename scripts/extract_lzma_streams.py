#!/usr/bin/env python3
"""
extract_lzma_streams.py -- extract all LZMA streams from an RTL867x flash dump.

The RTL8676S firmware stores the app + web UI as many standard .lzma streams
(props 0x5D = lc3/lp0/pb2, 8MB dict) concatenated. binwalk finds them; this
decompresses each with Python's lzma FORMAT_ALONE.

Workflow:
  1. On Kali: binwalk <dump> > binwalk_results.txt   (lists "LZMA ... uncompressed size: N")
  2. py extract_lzma_streams.py <dump> <binwalk_results.txt> <outdir>

Produces:
  <outdir>/streams/NNNN_0xOFFSET.bin   each decompressed stream
  <outdir>/all_decompressed.bin        all concatenated
  <outdir>/strings_all.txt             ASCII strings (>=5)
  <outdir>/pages.txt                   list of *.htm pages found
"""
import re, sys, os, lzma, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("binwalk_txt")
    ap.add_argument("outdir")
    a = ap.parse_args()

    d = open(a.dump, "rb").read()
    rows = []
    for line in open(a.binwalk_txt, encoding="utf-8", errors="replace"):
        m = re.match(r'\s*(\d+)\s+0x[0-9A-Fa-f]+\s+LZMA.*uncompressed size:\s*(\d+)', line)
        if m:
            rows.append((int(m.group(1)), int(m.group(2))))

    sdir = os.path.join(a.outdir, "streams")
    os.makedirs(sdir, exist_ok=True)
    combined = bytearray()
    ok = 0
    for i, (off, usize) in enumerate(rows):
        try:
            got = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[off:])
        except Exception:
            continue
        if not got:
            continue
        ok += 1
        open(os.path.join(sdir, f"{i:04d}_0x{off:06X}.bin"), "wb").write(got)
        combined += got

    open(os.path.join(a.outdir, "all_decompressed.bin"), "wb").write(combined)
    S = [m.group().decode("ascii", "replace")
         for m in re.finditer(rb'[\x20-\x7e]{5,}', bytes(combined))]
    open(os.path.join(a.outdir, "strings_all.txt"), "w", encoding="utf-8").write("\n".join(S))
    pages = sorted(set(re.findall(r'([A-Za-z0-9_]+\.htm)', "\n".join(S))))
    open(os.path.join(a.outdir, "pages.txt"), "w", encoding="utf-8").write("\n".join(pages))

    print(f"streams listed : {len(rows)}")
    print(f"decompressed   : {ok}")
    print(f"combined bytes : {len(combined)}")
    print(f"strings        : {len(S)}")
    print(f"web pages      : {len(pages)}")

if __name__ == "__main__":
    main()
