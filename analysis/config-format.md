# Config format analysis — RTL8676S

## KEY FINDING: config is COMPRESSED (LZMA), not encrypted
The boot log prints the loader decompressing each config block on startup:
```
uncompress: preLen:5404, unPreLen:35493                 (default/factory settings blob)
flash hw config addr:0xbfc04000 size:8192
uncompress: preLen:420,  unPreLen:1404                  (HW config: 420 -> 1404 bytes)
flash sw config addr:0xbfffc000 size:16384
uncompress: preLen:6954, unPreLen:39158                 (SW config: 6954 -> 39158 bytes)
```
- Loader banner: "RTL867X LOADER (LZMA)" -> the compressor is **LZMA** (Realtek's variant).
- So the high entropy (~7.96/8) we measured on the SW-config dump = COMPRESSION, not encryption.
  => The config is RECOVERABLE by decompressing it. No key needed (probably).

## Our SW-config dump cross-check
- We dumped `d 0xbfffc000 4000` (16384 bytes) -> dumps/sw_config.bin.
- Boot log says the SW config compressed length (preLen) = **6954** bytes, which inflates to
  **39158** bytes. 6954 = 0x1B2A. 
- Recall our dump's header first word: `00 00 1B 2A` = **0x1B2A = 6954**. THAT MATCHES preLen!
  => The 16KB region is: [header/length fields][6954-byte LZMA stream][padding to 16KB].
  => Byte offset of the LZMA payload: header is likely 16 bytes (0x10). After the header our
     dump showed data starting at 0x10 (`5E 24 02 D8 ...`). The real LZMA stream likely starts
     a few bytes in. Need to find the exact LZMA start.

## Header bytes (dumps/sw_config.bin, offset 0)
```
00 00 1B 2A | 06 D1 30 65 | 00 00 40 00 | 00 00 1E 12 | 5E 24 02 D8 4D BD ...
  len=6954      ? cksum?      0x4000=16384   ?            <- payload begins here?
                             (region size)
```
Interpretation (big-endian 32-bit, Realtek is big-endian MIPS):
- +0x00 = 0x00001B2A = 6954  -> compressed length (matches boot "preLen:6954")
- +0x04 = 0x06D13065         -> likely a checksum/CRC of the payload
- +0x08 = 0x00004000 = 16384 -> region size
- +0x0C = 0x00001E12         -> ? (maybe uncompressed-len-related or version; 0x1E12=7698, not 39158)
- +0x10 ...                  -> payload (LZMA stream, possibly headerless/Realtek-framed)

NOTE: Realtek RTL8xxx LZMA is often a "raw"/headerless LZMA or uses a custom small header, NOT the
standard .lzma (5-byte props + 8-byte size) container. Standard `lzma -d` may fail; may need
`xz`/`lzma` with explicit props, or the Realtek `lzma` tool, or carve & brute properties.

## How to decode (plan, do in analysis/)
1. Carve the compressed payload from dumps/sw_config.bin:
   - try starting at +0x10 (and +0x0C, +0x08) for 6954 bytes.
2. Try standard decompressors on the carve:
   - `xz -dc --format=lzma`  /  `lzma -dc`  /  7z  /  python `lzma` module with FORMAT_ALONE and
     FORMAT_RAW (try several lc/lp/pb filter props).
3. If standard fails (likely, Realtek uses a custom LZMA framing): dump the FULL flash, find the
   loader's decompressor routine, and replicate it (or run the loader's own `uncompress`).
4. Success check: output should be ~39158 bytes of readable MIB/config text (SSID [REDACTED_SSID],
   PSK [REDACTED_WIFI_PSK], PPPoE creds, ACS URL, etc. — we already see these in the boot log).

## Shortcut reality check
The boot log ALREADY prints the live config in plaintext as it applies the MIBs (SSID, WPA PSK,
ACL IPs, ACS URL). So for "what are the settings", the boot log is the fastest source. Decoding
the raw config block is the deeper RE exercise (understand the MIB/TLV format + Realtek LZMA).

## Tools to add to scripts/
- carve_config.py : slice N bytes at offset from a .bin
- try_lzma.py     : attempt FORMAT_ALONE / FORMAT_RAW (sweep lc/lp/pb) decompress
