# Research notes — RTL8676S / GD25Q32 / Lexra

Collected 2026-10-09 from web research. Links at bottom. Verify chip-specific details against
the actual datasheet / boot log before relying on them.

## SoC: Realtek RTL8676S (family RTL867x)
- Role: CPU + xDSL (ADSL/VDSL) SoC for home gateways. Paired in typical designs with a Realtek
  LAN switch/PHY (e.g. RTL8271B class) and a Realtek WLAN part.
- CPU core: **Realtek Lexra** — a licensed core implementing a MIPS-I-LIKE ISA, but NOT identical:
  * Classic Lexra omitted the 4 unaligned load/store ops (lwl/lwr/swl/swr) and (early parts)
    multiply/divide; added Lexra DSP extensions. Per-chip variation is real — some later Realtek
    parts re-added ULS (CPU_HAS_ULS) or are full MIPS32R2 (e.g. RTL8197F). CONFIRM for RTL8676S
    from its boot CPU revision string.
  * Practical impact for disassembly: Ghidra/IDA MIPS (32-bit, pick endianness) is the closest
    start, but some opcodes may mis-decode; a custom SLEIGH/RLX handling may be needed. Search
    GitHub for "lexra"/"rlx" binutils/disassembler forks and the OpenWrt Realtek port source.
- Endianness: Realtek RTL8xxx are typically **big-endian MIPS**. CONFIRM (affects disassembly +
  how multi-byte config fields are read). The config header `00 00 1B 2A` reading as 0x1B2A and
  `00 00 40 00` as 0x4000 is consistent with BIG-ENDIAN 32-bit fields.
- Linux/OpenWrt: vendor used an old kernel (2.6.30-era); NO mainline/OpenWrt support for RTL867x
  Lexra. So this firmware is the vendor RTOS blob, not Linux.

## Flash: GigaDevice GD25Q32 (SPI NOR)  [CORRECTED — was assumed GD25Q128]
- ACTUAL chip, confirmed by flashrom chip-off read: **GD25Q32(B), 4 MB (32 Mbit)**, JEDEC
  **C8 40 16**. (The boot log printed only the short id "c8/40" and the bootloader REPORTED
  "Flash Size: 16M" — that was WRONG/a default. Early notes here assumed GD25Q128/16MB from the
  short id; the chip-off proved it is 4 MB. Lesson: never trust the bootloader's reported size;
  read the real JEDEC RDID / chip-off to confirm.)
- Capacity 4 MB; 4 KB sector x 1024. Voltage 2.7-3.6V (3.3V typical). Package SOIC-8/SOP-8.
  133 MHz. Quad-SPI capable.
- Standard SPI NOR -> a bare 3.3V CH341A + SOIC-8 clip can read it directly (no 1.8V adapter,
  unlike the ZLT S20 NAND). flashrom identifies it as "GD25Q32(B)".
- SOIC-8 pinout (standard SPI NOR):
    1 /CS   2 DO(MISO)  3 /WP   4 GND
    5 DI(MOSI) 6 CLK    7 /HOLD 8 VCC(3.3V)

## Topnet / TR-069 context
- ACS seen: http://acs3.topnet.tn:1111/ACS-INTF  (CWMP/TR-069 remote management).
- Firmware V7.0421.01 (2021-04-14). RTOS tasks include CWMPSRV/CWMPCLT/CWMPDL (TR-069),
  PPPoE/ppp, l2tp, pptp-client, Telnet, UPNP, WSC, dhcpv6, SNMP, DDNS, NTP, BFTPD/FTPC.

## Config format (to crack later)
- SW config @0xBFFFC000 (16KB) and HW config @0xBFC04000 (8KB).
- SW config dump is high-entropy (~7.96/8) => compressed and/or encrypted. Header:
  `00 00 1B 2A 06 D1 30 65 00 00 40 00 00 00 1E 12 5E 24 02 D8 ...`
  * 0x00004000 field = 16384 = block size (big-endian).
  * 0x1B2A (6954) possibly a used-length or checksum seed.
- Realtek RTL8xxx vendor configs are commonly LZMA-compressed and/or scrambled with a routine in
  the firmware. Plan: dump full flash, locate the config read/decrypt routine (strings like
  "config", "flash", "lzma", or the ACS URL cross-ref), recover the codec/key.

## Reverse-engineering toolchain (planned, in analysis/)
- binwalk -e flash_full.bin   (find LZMA/compressed app, headers, embedded files, strings)
- strings -n 6 flash_full.bin (ACS URL, SSIDs, usernames, cert blobs, version banners)
- Ghidra with MIPS 32-bit (big-endian first) to load the app; watch for Lexra decode anomalies.
- Compare against OpenWrt Realtek-Lexra sources for memory-map / register hints.

## Links (for datasheets/ and reference)
- RTL8676 = Lexra core, no OpenWrt: https://lists.openwrt.org/pipermail/openwrt-devel/2017-April/017014.html
- Realtek/Lexra ISA discussion: https://forum.openwrt.org/t/working-realtek-soc-rtl8196e-97d-97f-in-last-master/70975
- Lexra background (MPR 1998): https://www.cecs.uci.edu/~papers/mpr/MPR/19980216/120203.pdf
- Lexra company/core: https://www.probell.com/lexra
- GD25Q32 datasheet (GigaDevice): search "GD25Q32 datasheet" (4 MB SPI NOR, JEDEC C8 40 16)
- flashrom supported-flash list (GD25Q32 entry): https://www.flashrom.org/supported_hardware/supported_flash_chips.html
- Ghidra: https://en.wikipedia.org/wiki/Ghidra
