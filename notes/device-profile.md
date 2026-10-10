# Device profile — RTL8676S Topnet router

Confirmed facts, grounded in the UART boot log + bootloader `info`/`help` + chip IDs + research.
Items marked (?) are not yet verified on this exact unit.

## Identity  (AUTHORITATIVE from CLI `show version`)
- Model: **TOPNET ADSL Router TD8963N** ; Manufacturer **TP-Link** (OUI [REDACTED_OUI]); ProductClass IGD;
  "ADSL SoHo Router". Role: Topnet (Tunisia ISP) ADSL/WiFi home gateway, ISP-managed via TR-069.
- Serial Number: [REDACTED_SERIAL] ; runtime MAC [REDACTED_MAC].
- Application/Firmware version: **V7.0421.01** (Build Apr 14 2021 10:28:23)
- SDK Version: **SDK V1.3.1** ; Hardware Version string: **8671x**
- Bootloader: **RTL867X LOADER (LZMA)**, Version 00.01.02a-rc (Jan 31 2018 18:45:10)
- Loader MAC placeholder: 00:23:79:11:22:33 (Realtek OUI; the real NIC MAC is [REDACTED_MAC])
- ACS (TR-069): `http://acs3.topnet.tn:1111/ACS-INTF` (CWMP 7547)
- Line status: internet closed/dead (device retired) — owner's own hardware.
- Full live CLI enumeration: notes/cli-reference.md ; raw: captures/cli-session-raw.txt.

## SoC / CPU
- **Realtek RTL8676S** — CPU + xDSL. (Family: RTL867x.)
- CPU core: **Realtek Lexra** — a MODIFIED MIPS-like ISA (NOT standard MIPS-I). IMPORTANT for
  later disassembly: standard MIPS decoders may mis-handle some instructions (Lexra omits/moves
  some MIPS ops). Vendor kernel historically Linux 2.6.30-era; NOT OpenWrt-supported.
- Companion chips (typical for this family, VERIFY on board): RTL8271B-class LAN PHY/switch,
  a Realtek WLAN part (boot log shows task `rtl8670` + `auth_wlan`/`WSC` -> integrated WiFi).
- Memory map: MIPS/Lexra style — kseg0 cached 0x80000000, kseg1 uncached 0xA0000000,
  reset/flash base physical 0x1FC00000 -> flash window **0xBFC00000** (uncached). CONFIRMED by
  boot log "flash hw config addr:0xbfc04000" / "flash sw config addr:0xbfffc000".

## RAM
- DDR via Realtek "6256/6257" DDR controller ("8676(>M) + 6256/6257 decide use DDR mode").
- Exact size not printed; task stacks occupy ~0x5000_0000 range, memory pool 11.66 MB allocated.
  TODO: read exact DRAM size (likely 32 MiB for this family) via `memsize` / chip markings.

## Companion chips (CONFIRMED from boot log)
- LAN/NIC: **RTL8196B** 10/100 switch ("Probing RTL8186 NIC... chip name: 8196B revid 0").
- WLAN: **RTL8192E** 2.4GHz (MAC/PHY param files RTL8192E_...); driver v3.6.3 (2017-08-23);
  WLAN MAC [REDACTED_MAC] (OUI [REDACTED_OUI] Realtek). "eric-8822"/RTL8822 strings also present.
- DSL: integrated ADSL/VDSL (ATM PVC engine; adslCfgMode modemask 0xff).
- SoC IDs: gSocId=0x63330000, "867x ver = Q", AFE_ver 0x3430/0x686.

## Flash  (CORRECTED by chip-off 2026-10-10)
- **GigaDevice GD25Q32(B)** SPI NOR, **4 MB** (32 Mbit), 3.3V, SOIC-8. CONFIRMED by flashrom
  chip-off read: `Found GigaDevice flash chip "GD25Q32(B)" (4096 kB, SPI)`.
- The bootloader `info` "Flash Size: 16M" and boot-log `sector 0x1000 x 1024` were MISLEADING /
  a default — the real chip is **4 MB**, not 16 MB. This is why tftpbk capped at 4MB and
  `d 0xC0000000` hung: 4MB is the WHOLE chip. There is NO hidden upper 12MB.
- Chip-off dump (firmware/flash_full_chipoff_4MB.bin, md5 809ba341...) == the TFTP dump
  (flash_first4mb.bin) byte-for-byte EXCEPT the last 32 bytes at 0x3FFFE0 (config checksum tail:
  TFTP read 00, chip-off reads FF). So the earlier TFTP dump was already the complete firmware.
- Memory-mapped at 0xBFC00000 (window = full 4MB, 0xBFC00000-0xC0000000).
- Known internal addresses from boot log:
  * flash HW config: 0xBFC04000, size 0x2000 (8 KB)  -> phys 0x4000
  * flash SW config: 0xBFFFC000, size 0x4000 (16 KB) -> phys 0x3FC000
  * eraseUnusedFlash region: 0xBFE20000 .. 0xBFFF0000 (phys ~0x220000..0x3F0000)

## Boot loader (RTL867X) — from `help`
Commands: help, info, reboot, run [app addr] [entry addr], r [addr], w [addr] [val],
d [addr] <len>, mac, bootline, entry [address], load [address], xmodem [address],
tftp [ip] [server ip] [file], tftpbk [size] [clientip] [serverip] [file], multicast,
flashsize [...], memsize [...], uart [0 enable /1 disable].
- `info`: Load/Entry 0x80000000; App 0x9FC10000; Flash 16M; MII sel 0 (internal PHY); UART enabled.
- Entry to loader: **press ESC during power-on**.

## OS / firmware architecture
- NOT embedded Linux. Boot log shows an **RTOS** with named tasks via `registerTask`
  (CFGTASK, STPMAIN, CLITASK, XTCPIP, SNMP, PPPoE, TFTPD, DHCP, Telnet, UPNP, CWMPSRV/CWMPCLT
  (TR-069), rtl8670, auth_wlan, WSC, dhcpv6c/d, pptp-client, l2tp, ...). Single monolithic
  firmware blob (LZMA-compressed app). No rootfs / no /bin/sh shell.

## Config storage  (UPDATED: it's COMPRESSED, not encrypted)
- SW config @0xBFFFC000 (16KB), HW config @0xBFC04000 (8KB). Default settings blob also present.
- Boot log shows the loader DECOMPRESSING them (LZMA): "uncompress: preLen:6954, unPreLen:39158"
  for SW config. preLen 6954 = 0x1B2A = the first word of our dump's header -> confirms layout:
  [header][6954-byte LZMA stream][pad to 16KB]. High entropy was compression, not encryption.
- => Config is RECOVERABLE by decompressing (likely no key). See analysis/config-format.md.
- Config model = Realtek "MIB chains" (named TLV records). Live values are even printed in
  plaintext in the boot log (SSID [REDACTED_SSID], WPA PSK [REDACTED_WIFI_PSK], ACS URL, ACL IPs)
  -> see notes/findings-from-bootlog.md.

## UART (serial console)
- 4 pads: GND, TX (3.3V, flickers at boot), RX, VCC (3.3V steady).
- RX identified by LOAD-SAG test (330Ohm pad->GND: RX collapses to 0V, VCC holds 3.3V).
- Logic level **3.3V** -> CP2102 connects directly, no level shifter.
- Baud: 115200 (clean console). picocom `-g` used to log.

## Status
Flash fully dumped (4 MB, two independent methods) and analysed; firmware web UI extracted; config
decoded; device fully identified via the `ADSL#` CLI. Flash part corrected to GD25Q32 after chip-off.
Remaining open item for deeper work: disassemble the app code (MIPS/Lexra, big-endian) in Ghidra.
