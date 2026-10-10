#!/usr/bin/env python3
"""
rtl_hex2bin.py -- read an RTL867X "d" hexdump and write the raw bytes to a .bin

Parses every line of the form:
    0xBFFFC000: 00 00 1B 2A 06 D1 30 65 00 00 40 00 00 00 1E 12 ...*..0e..@.....
Ignores blank lines, prompts, and the ASCII column. Bytes are taken in the
order the lines appear (already address-sorted in a normal dump).

Usage:
    python3 rtl_hex2bin.py input.log output.bin
    python3 rtl_hex2bin.py input.log output.bin --strings   # also dump ASCII strings
"""
import re, sys, argparse

# 0xADDR:  then 1..16 hex byte pairs  (stop before the ASCII column)
LINE_RE = re.compile(r'0x[0-9A-Fa-f]+:\s*((?:[0-9A-Fa-f]{2}\s+){1,16})')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--strings", action="store_true")
    a = ap.parse_args()

    data = bytearray()
    nlines = 0
    with open(a.infile, "r", errors="replace") as f:
        for line in f:
            m = LINE_RE.search(line)
            if not m:
                continue
            for h in m.group(1).split():
                data.append(int(h, 16))
            nlines += 1

    with open(a.outfile, "wb") as f:
        f.write(data)

    print(f"lines parsed : {nlines}")
    print(f"bytes written: {len(data)} (0x{len(data):X})")
    print(f"output       : {a.outfile}")

    if a.strings:
        print("\n--- ASCII strings (>=4) ---")
        for m in re.finditer(rb'[\x20-\x7e]{4,}', bytes(data)):
            print(m.group().decode("ascii", "replace"))

if __name__ == "__main__":
    main()
