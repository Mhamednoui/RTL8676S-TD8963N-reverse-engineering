# TOPNET TD8963N (Realtek RTL8676S) — Reverse Engineering

A hands-on reverse-engineering / learning project on a **retired Topnet (Tunisia) ISP home
gateway** — model **TOPNET ADSL Router TD8963N** (made by TP-Link), built on a **Realtek
RTL8676S** (RTL867x "8671x", Lexra core) SoC, firmware **V7.0421.01 / SDK V1.3.1**. The
device's internet line is closed/dead; it is the owner's own hardware, studied for learning.
Goal: understand the device end-to-end — bootloader, flash layout, firmware, config format,
web UI, live CLI — and document everything for a possible GitHub publish.

> Sibling project: `../ZLT_S20_Router/` (TOZED ZLT S20, ARM ZX297520V3). Techniques carry over.

## TL;DR status (complete)
- **Access:** UART serial console → `<RTL867X>` boot loader (ESC at power-on) and the `ADSL#` RTOS
  CLI. Services: 21 ftp, 23 telnet, 53 dns, 80 http, 443 https, 7547 cwmp (TR-069).
- **Dumping:** full flash obtained two ways — over the network (`tftpbk`) and by **chip-off** of the
  GigaDevice **GD25Q32 (4 MB)** SPI-NOR with a CH341A programmer. Flash is memory-mapped at
  **0xBFC00000** (MIPS/Lexra kseg1). The bootloader's "16M" was wrong — the chip is **4 MB**.
- **Firmware:** the app is ~132 concatenated **LZMA** streams; decompressed and carved into the full
  web UI. The config block is **LZMA-compressed, not encrypted** (high entropy was compression) and
  decodes to an XML settings file.
- **Findings:** see `SECURITY_FINDINGS.md` (educational, redacted).

See `notes/LOG.md` for the running log and `notes/device-profile.md` for the hardware facts.

## Folder layout
- `notes/`      — LOG.md (session log), device-profile.md, research.md, uart-and-dumping.md, cli-reference.md, findings-from-bootlog.md
- `analysis/`   — how the firmware/config were decompressed and analysed; the flash map; vuln review
- `scripts/`    — helper scripts (LZMA stream extractor, hexdump→bin converters, rtl_clean.py)
- `SECURITY_FINDINGS.md` — redacted, educational security write-up

## What is NOT in this public repo (and why)
This is the **redacted, public** copy. The following are intentionally **omitted** because they
contain the owner's live secrets (ISP/WiFi passwords, serial, email, admin passwords) and the
vendor's copyrighted firmware:
- the raw flash dumps (`firmware/*.bin`), the decoded config (`sw_config_decompressed.bin`),
- the extracted firmware tree / strings (`analysis/extracted/`), and raw serial captures
  (`captures/*.log`, `cli-session-raw.txt`).

All credentials in the remaining docs are replaced with `[REDACTED_*]` placeholders. The notes still
describe the exact commands and offsets used, so the method is fully reproducible on your own device.

## Reproduce it on your own device
The firmware image is **not** shipped (it's the vendor's and holds personal secrets). To get your
own, on your own TD8963N:
1. **UART:** solder to the board's TX/RX/GND pads (3.3V), 115200 8N1; press **ESC** at power-on for
   the `<RTL867X>` boot loader. (`notes/uart-and-dumping.md` has the wiring + how pins were found.)
2. **Dump the 4 MB flash** either over the network with `tftpbk` from the boot loader to a TFTP
   server on your PC, or by **chip-off** of the GD25Q32 with a CH341A + SOIC-8 clip + flashrom.
3. **Extract:** run `scripts/extract_lzma_streams.py` on the dump to decompress the ~132 LZMA
   streams (the web UI + app). Decode the config block with the raw-LZMA method in
   `analysis/config-format.md` / `config-decoded.md`.
Every command, offset and parameter used is in `notes/` and `analysis/`.

## Tools used
UART: USB-TTL adapter (CP2102) + a logic analyzer for the baud. Flash: CH341A programmer + SOIC-8
clip, `flashrom`. Analysis: Python standard library only (`lzma`), `binwalk`, Kali Linux.

## Licence
Documentation and scripts in this repo: MIT (do as you like, no warranty). The analysed firmware
is the property of TP-Link / Realtek / Topnet and is **not** included or redistributed here.

## Safety / scope
Owner's own, de-provisioned device (dead line). Studying firmware/structure for learning and
responsible disclosure. **Not** for attacking a live network or anyone else's device, and the
recovered credentials are the owner's own and are not published. See `SECURITY_FINDINGS.md`.
