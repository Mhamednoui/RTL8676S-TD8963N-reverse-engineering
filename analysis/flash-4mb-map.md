# Analysis of the first 4 MB dump (firmware/flash_first4mb.bin)

Source: `tftpbk 0x400000 ...` = flash 0x000000-0x400000 (mapped window 0xBFC00000-0xC0000000).
tftpbk CANNOT exceed 4MB (hard wall) and has no offset arg; `d` reads only within the 4MB window
(0xC0000000 hangs). So the CPU's directly-visible flash window is **exactly the first 4 MB**; the
other 12 MB of the 16 MB GD25Q128 is NOT in this address window (bank-switched or separate) and
needs chip-off (CH341A, 3.3V NOR, no adapter) to read.

## Region map (256 KB granularity, entropy H + fill)
```
0x000000-0x040000  H=7.65  some FF   -> BOOTLOADER + config area (0xBFC00000)
                                        (HW cfg @0x04000, SW cfg @0x3FC000 are in here)
0x040000-0x200000  H=8.00  0% FF     -> COMPRESSED MAIN APP IMAGE (~1.75 MB, LZMA)
0x200000-0x3C0000  FF=100%           -> ERASED / free space
0x3C0000-0x400000  mostly FF         -> tail (small data)
```
=> The whole active firmware (loader + app + config) fits in the first ~2 MB. The erased gap
after it suggests the upper banks are a second image slot / spare, likely less critical.

## Headers / signatures
- First bytes @0x0: `10 00 00 FF 00 00 00 00 10 00 01 18 ...` = a loader descriptor/vector table
  (repeating `10 00 FF xx` records). Not a standard container magic.
- Many `5D 00 00` (LZMA props 0x5d) and `hsqs`/JFFS2 hits inside 0x40000-0x200000 are mostly
  FALSE POSITIVES (random bytes at H=8.0). One `5D` at 0x28b sits in the low-entropy loader.
- App @0x40000 starts raw high-entropy (no standard LZMA/uImage magic) -> **Realtek CUSTOM LZMA
  framing** (same as the config block; standard lzma/xz decode fails).

## Strings
- Only ~3628 ASCII strings in 4MB, few meaningful ("CWMPNotify.txt", "FW4TKeY") -> because the
  app is compressed. Real strings appear only after decompression.

## Config blocks (within this dump)
- HW config @ file offset 0x04000 (0xBFC04000): LZMA, boot log preLen:420 unPreLen:1404.
- SW config @ file offset 0x3FC000 (0xBFFFC000): LZMA, preLen:6954 unPreLen:39158.
  (We also dumped it separately -> dumps/sw_config.bin; header word 0x1B2A = 6954 = preLen.)

## How to extract the firmware contents
Standard tools (lzma/xz/binwalk default) will struggle due to Realtek custom LZMA framing.
Options:
1. **binwalk on Kali** (has entropy scan + many extractors): `binwalk -e -M flash_first4mb.bin`.
   Run it on Kali where binwalk exists (not on the Windows host). Serve results back.
2. **Replicate Realtek LZMA**: find the loader's decompressor in the first 0x40000 and mimic it,
   or feed the stream to a Realtek-aware lzma (some "rtk lzma"/squashfs-rtk tools exist).
3. **Boot log already prints the live config** (SSID/PSK/ACS/ACLs) -> notes/findings-from-bootlog.md,
   so the *settings* are known even without decompressing the config.

## To get the FULL 16 MB
- tftpbk wall = 4MB; window = 4MB. Upper 12MB not directly addressable.
- Cleanest: **chip-off the GD25Q128** (SOIC-8, 3.3V NOR) with the CH341A (NO 1.8V adapter needed,
  unlike the S20 NAND) + flashrom/NeoProgrammer -> full 16MB in one read.
- Or reverse the bank-switch register (more work).

## TODO
- [ ] Run `binwalk -e` on Kali against flash_first4mb.bin; bring back extracted app/rootfs.
- [ ] Decompress config (Realtek LZMA) -> plaintext MIB.
- [ ] Decide if upper 12MB is worth chip-off.
