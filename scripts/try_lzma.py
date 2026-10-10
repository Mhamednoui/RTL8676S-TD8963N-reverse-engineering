#!/usr/bin/env python3
"""
try_lzma.py -- carve a region from a .bin and try to LZMA-decompress it several ways.

Realtek RTL867x config blocks are LZMA-compressed (boot log: "uncompress: preLen:N unPreLen:M").
The framing is often non-standard, so we try multiple offsets/formats and report what works.

Usage:
    py try_lzma.py dumps/sw_config.bin
    py try_lzma.py dumps/sw_config.bin --offset 0x10 --len 6954
    py try_lzma.py dumps/sw_config.bin --sweep        # try offsets 0..32 x several formats

On success it writes <input>.decompressed and prints the first chars + any strings.
"""
import sys, argparse, lzma

def attempts(blob):
    """Yield (label, decompressed_bytes) for whatever decodes."""
    # 1) standard .lzma (FORMAT_ALONE)
    try:
        yield "FORMAT_ALONE", lzma.decompress(blob, format=lzma.FORMAT_ALONE)
    except Exception:
        pass
    # 2) xz
    try:
        yield "FORMAT_XZ", lzma.decompress(blob, format=lzma.FORMAT_XZ)
    except Exception:
        pass
    # 3) raw LZMA1 with swept properties (lc,lp,pb) and a few dict sizes
    for lc in range(0, 5):
        for lp in range(0, 3):
            for pb in range(0, 5):
                for dict_size in (1 << 16, 1 << 20, 1 << 23):
                    filt = [{"id": lzma.FILTER_LZMA1, "dict_size": dict_size,
                             "lc": lc, "lp": lp, "pb": pb}]
                    try:
                        out = lzma.decompress(blob, format=lzma.FORMAT_RAW, filters=filt)
                        if out:
                            yield f"RAW lc={lc} lp={lp} pb={pb} dict={dict_size:#x}", out
                            return  # first raw hit is enough
                    except Exception:
                        pass

def try_at(data, off, length, want_strings=True):
    blob = data[off:off+length] if length else data[off:]
    for label, out in attempts(blob):
        print(f"  [OK] offset={off:#x} {label} -> {len(out)} bytes")
        return out, label
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--offset", default="0x10")
    ap.add_argument("--len", default="0")   # 0 = to end
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    data = open(a.infile, "rb").read()

    offs = range(0, 33) if a.sweep else [int(a.offset, 0)]
    length = int(a.len, 0)

    for off in offs:
        out, label = try_at(data, off, length)
        if out:
            outpath = a.infile + ".decompressed"
            open(outpath, "wb").write(out)
            print(f"\nWROTE {outpath} ({len(out)} bytes) via {label} at offset {off:#x}")
            print("first 200 bytes:\n", out[:200])
            import re
            strs = re.findall(rb'[\x20-\x7e]{4,}', out)
            print(f"\n{len(strs)} strings; first 40:")
            for s in strs[:40]:
                print("   ", s.decode("ascii", "replace"))
            return
    print("No LZMA variant decoded. Realtek framing is likely custom -> need the loader's")
    print("decompressor (dump full flash, find the routine) or correct offset/props.")

if __name__ == "__main__":
    main()
