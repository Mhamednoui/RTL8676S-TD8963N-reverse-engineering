#!/usr/bin/env python3
"""
rtl_clean.py -- clean an RTL867X "d" serial dump and render it human-readable.

Pipeline:
  1. keep ONLY real data lines ( 0xADDR: <hex bytes> [ascii] ), drop prompts/blanks/echo
  2. rebuild the raw bytes
  3. write:
       <out>.bin   raw binary
       <out>.hex   clean canonical hexdump (addr: 16 hex  | ascii)
       <out>.txt   extracted human-readable ASCII strings (>=4 chars)
     and print a summary + the strings to the screen.

Usage:
  python3 rtl_clean.py dump.log config
      -> config.bin  config.hex  config.txt
  python3 rtl_clean.py dump.log config --base 0xBFFFC000
      (force the display base address; otherwise taken from the first line)
"""
import re, sys, argparse

LINE_RE = re.compile(r'0x([0-9A-Fa-f]+)\s*:\s*((?:[0-9A-Fa-f]{2}\s+){1,16})')

def parse(path):
    rows = []
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = LINE_RE.search(line)
            if not m:
                continue
            addr = int(m.group(1), 16)
            data = bytes(int(h, 16) for h in m.group(2).split())
            rows.append((addr, data))
    return rows

def render_hex(base, data, width=16):
    out = []
    for off in range(0, len(data), width):
        chunk = data[off:off+width]
        hexs = " ".join(f"{b:02X}" for b in chunk)
        hexs = f"{hexs:<{width*3-1}}"
        ascii_ = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{base+off:08X}: {hexs}  |{ascii_}|")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outbase", help="output name without extension")
    ap.add_argument("--base", help="force display base addr, e.g. 0xBFFFC000")
    ap.add_argument("--minstr", type=int, default=4, help="min string length (default 4)")
    a = ap.parse_args()

    rows = parse(a.infile)
    if not rows:
        sys.exit("No data lines found. Check the log format (expect '0xADDR: hex...').")

    data = bytearray()
    for _, d in rows:
        data.extend(d)
    data = bytes(data)

    base = int(a.base, 16) if a.base else rows[0][0]

    binf, hexf, txtf = a.outbase+".bin", a.outbase+".hex", a.outbase+".txt"

    with open(binf, "wb") as f:
        f.write(data)

    hexdump = render_hex(base, data)
    with open(hexf, "w") as f:
        f.write(hexdump + "\n")

    strings = [m.group().decode("ascii", "replace")
               for m in re.finditer(rb'[\x20-\x7e]{%d,}' % a.minstr, data)]
    with open(txtf, "w") as f:
        f.write("\n".join(strings) + "\n")

    print(f"lines parsed : {len(rows)}")
    print(f"bytes        : {len(data)} (0x{len(data):X})")
    print(f"base addr    : 0x{base:08X}")
    print(f"written      : {binf}, {hexf}, {txtf}")
    print(f"\n--- readable strings ({len(strings)}) ---")
    for s in strings:
        print(s)

if __name__ == "__main__":
    main()
