#!/usr/bin/env python3
"""
hexdump_to_bin.py -- convert an RTL867X "d <addr> <len>" serial hexdump into a raw .bin

Handles lines like:
    0xBFC04000: 00 00 01 A4 00 66 30 7A 00 00 40 00 00 00 1E 12 .....f0z..@.....
    <RTL867X>d 0xbfc04000 2000      (prompt/command echo lines are ignored)

Usage:
    python3 hexdump_to_bin.py rtl_dump.log out.bin
    python3 hexdump_to_bin.py rtl_dump.log out.bin --strings   # also print ASCII strings
    python3 hexdump_to_bin.py rtl_dump.log out.bin --expect 0x2000   # warn if size != expected

It parses ONLY lines that start with an address of the form 0x........:
Reconstructs bytes in address order; warns on gaps/overlaps so a dropped
serial line is visible rather than silently corrupting the image.
"""
import re
import sys
import argparse

# a data line: optional leading junk, then  0xADDR:  then hex byte pairs
LINE_RE = re.compile(
    r'(?:0x)?([0-9A-Fa-f]{6,8})\s*:\s*((?:[0-9A-Fa-f]{2}\s+){1,16})'
)

def parse(path):
    """Return list of (address:int, data:bytes) for every data line found."""
    rows = []
    with open(path, 'r', errors='replace') as f:
        for raw in f:
            m = LINE_RE.search(raw)
            if not m:
                continue
            addr = int(m.group(1), 16)
            hexpart = m.group(2).split()
            data = bytes(int(h, 16) for h in hexpart)
            rows.append((addr, data))
    return rows

def assemble(rows):
    """Stitch rows into one contiguous bytearray, reporting gaps/overlaps."""
    if not rows:
        raise SystemExit("No hexdump data lines found. Check the log / format.")
    rows.sort(key=lambda r: r[0])
    base = rows[0][0]
    out = bytearray()
    cur = base
    issues = 0
    for addr, data in rows:
        if addr < cur:
            # overlap (duplicate line) -- skip the overlapping prefix
            skip = cur - addr
            if skip < len(data):
                out.extend(data[skip:])
                cur += len(data) - skip
            # fully-duplicate line: ignore
            continue
        if addr > cur:
            gap = addr - cur
            print(f"!! GAP of {gap} byte(s) at 0x{cur:08X} (dropped line?) -> padding 0xFF",
                  file=sys.stderr)
            out.extend(b'\xFF' * gap)
            cur += gap
            issues += 1
        out.extend(data)
        cur += len(data)
    return base, out, issues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("outbin")
    ap.add_argument("--strings", action="store_true", help="print ASCII strings (len>=4)")
    ap.add_argument("--expect", help="expected length (e.g. 0x2000) -> warn if mismatch")
    args = ap.parse_args()

    rows = parse(args.logfile)
    base, data, issues = assemble(rows)
    with open(args.outbin, "wb") as f:
        f.write(data)

    print(f"base addr : 0x{base:08X}")
    print(f"bytes     : {len(data)} (0x{len(data):X})")
    print(f"gaps      : {issues}")
    print(f"written   : {args.outbin}")

    if args.expect:
        exp = int(args.expect, 16) if args.expect.lower().startswith("0x") else int(args.expect)
        if len(data) != exp:
            print(f"!! size {len(data)} != expected {exp} (0x{exp:X})", file=sys.stderr)

    if args.strings:
        print("\n--- ASCII strings (>=4) ---")
        for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
            print(m.group().decode('ascii', 'replace'))

if __name__ == "__main__":
    main()
