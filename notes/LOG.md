# Work log — RTL8676S Topnet router

Newest entry on top. date — what I did — what I found — next step.

## 2026-10-09 (session 1) — project created; UART + bootloader access achieved
- Spun this off as its own project (was discovered while practicing CH341A for the ZLT S20).
  Owner's own retired Topnet router, dead line -> free to study/document fully.
- UART found on the board: 4 pads GND/TX/RX/VCC, **3.3V** logic.
  * GND by continuity to shield/jack. TX = 3.3V idle, drops/flickers during boot.
  * RX vs VCC resolved by LOAD-SAG test: 330Ohm from pad->GND while powered; RX collapsed to
    0V (weak pull-up input), VCC held 3.3V (stiff supply). RX = the one that sagged.
- picocom @ 115200 -> clean console. **Pressed ESC at power-on -> RTL867X boot loader shell.**
- `info`: RTL8676S; Load/Entry 0x80000000; App 0x9FC10000; **Flash 16M**; internal PHY; UART on.
- `help`: has `d` (mem dump), `r`/`w`, `tftp`/`tftpbk`, `xmodem`, `load`, `run`, `mac`, `bootline`.
- Boot log (early): "SPI flash found: id c8/40" = GigaDevice GD25Q128 16MB; sector 4KB x 1024.
  "flash hw config 0xbfc04000 / sw config 0xbfffc000". Firmware V7.0421.01 (Apr 14 2021).
  RTOS (registerTask: CWMP/TR-069, PPPoE, Telnet, rtl8670 WLAN...) -> NOT Linux, single blob.
  ACS: http://acs3.topnet.tn:1111/ACS-INTF.
- Flash mapped at **0xBFC00000** (MIPS/Lexra kseg1; reset vector 0x1FC00000). Deduced from the
  kseg0/kseg1 convention + confirmed by the loader's flash-config addresses.
- Dumped SW config: `d 0xbfffc000 4000` -> captured via picocom -g -> captures/sw_config.log.
  Cleaned with scripts/rtl_clean.py -> dumps/sw_config.{bin,hex,txt}. 4432 bytes parsed.
  **Config is ENCRYPTED/COMPRESSED**: entropy 7.958/8, all 256 byte values, no readable strings.
  Header `00 00 1B 2A 06 D1 30 65 00 00 40 00 ...`. Needs the firmware's codec/key to decode.
- RESEARCH: RTL8676S = Realtek **Lexra** core (modified MIPS ISA; standard MIPS tools imperfect);
  CPU+xDSL; ~32MB RAM typical; no OpenWrt/mainline support. GD25Q128 JEDEC C8 40 18, 3.3V, SOIC-8.
- TOOLING NOTE: on the Windows host use `py` (Python 3.13) not `python`. CH341A programmer works
  on Windows (VID_1A86 PID_5512, WCH driver OK) but flashrom-on-Kali "couldn't open" over VMware
  passthrough; NeoProgrammer needs correct chip + possibly Zadig/WinUSB. (That was for the S20 NAND.)
- NEXT: (1) user will capture full boot log -> AI downloads to captures/. (2) Full 16MB dump via
  tftpbk (preferred) or `d 0xbfc00000 1000000` -> firmware/flash_full.bin -> binwalk. (3) Board
  photos + chip part numbers -> photos/. (4) Find GD25Q128 datasheet -> datasheets/.

## 2026-10-09 (session 1b) — full boot log captured + analyzed (captures/boot.log, 30KB)
- Downloaded boot.log from Kali. Analyzed -> notes/findings-from-bootlog.md + analysis/config-format.md.
- BIG FINDING: config is **LZMA-COMPRESSED, NOT encrypted**. Boot log prints
  "uncompress: preLen:6954, unPreLen:39158" for SW config. preLen 6954 = 0x1B2A = first header
  word of our sw_config.bin dump -> layout [header][6954B LZMA][pad]. High entropy was compression.
  Config is decodable (see analysis/config-format.md). Realtek LZMA framing may be custom.
- Hardware CONFIRMED: SoC RTL8676S (gSocId 0x63330000, "867x ver Q"); LAN RTL8196B; WLAN RTL8192E
  (driver 3.6.3) MAC [REDACTED_MAC]; DDR via 6256/6257; GD25Q128 16MB; ADSL/VDSL DSL modem.
- Config/creds (plaintext in boot log, owner's own): SSID **[REDACTED_SSID]**, WPA2-PSK **[REDACTED_WIFI_PSK]**,
  LAN 192.168.1.1/24, WAN PPPoE vpi0/vci35, ACS http://acs3.topnet.tn:1111/ACS-INTF (CWMP 7547),
  WAN->local ACL permits 41.226.15.248/29 (Topnet mgmt). IPv6 on.
- Shortcut insight: the boot log already prints the live settings, so "what are the settings" is
  answered; decoding the raw block is the deeper RE exercise.
- NEXT: full 16MB flash dump (tftpbk) -> firmware/; then carve+decompress the config block; binwalk
  the app; try Ghidra (MIPS BE) on the app image noting Lexra quirks.

## 2026-10-09 (session 1c) — dumped first 4MB via tftpbk; mapped it
- tftpbk works but has a HARD 4MB wall (any size arg >4MB stops at 4MB; no offset arg; passing an
  extra addr arg -> BOOTP fallback fail). `d` reads only within 0xBFC00000-0xC0000000 (0xC0000000
  hangs). => CPU flash window = exactly the FIRST 4 MB. Upper 12 MB of the 16MB chip is bank-
  switched/separate -> needs chip-off (CH341A, 3.3V NOR, NO adapter) to read fully.
- TFTP transfer setup that worked: VMware BRIDGED to router; Kali 192.168.1.11; keep `ping
  192.168.1.1` running (forces ARP both ways, else "lookupARP failed"); server = atftpd (dnsmasq
  TFTP is read-only -> "unsupported request"; atftpd accepts the upload). dnsmasq held port 69 ->
  pkill first. Cmd: `tftpbk 0x400000 192.168.1.1 192.168.1.11 chunk.bin` -> "upld 4194304 bytes".
- Got firmware/flash_first4mb.bin (4194304 B). Switched VMware back to NAT, served over 192.168.235.129.
- MAP (analysis/flash-4mb-map.md): 0x0-0x40000 loader+config; 0x40000-0x200000 COMPRESSED APP
  (~1.75MB, H=8.0, Realtek custom LZMA); 0x200000-0x3C0000 erased FF; tail small. Active firmware
  fits in first ~2MB. Config LZMA (custom framing) -> standard lzma/xz fail; needs binwalk/Realtek
  lzma or the loader's decompressor. Live settings already known from boot log.
- NEXT: run `binwalk -e` on Kali against flash_first4mb.bin (binwalk not on Windows host); decide
  chip-off for full 16MB; attempt Realtek-LZMA config decode.

## 2026-10-09 (session 1d) — FIRMWARE EXTRACTED + vuln surface mapped
- binwalk (on Kali) -> analysis/binwalk_results.txt (155KB): the app = 134 standard .lzma streams
  (props 0x5D). Decompressed ALL with Python lzma FORMAT_ALONE (scripts/extract_lzma_streams.py)
  -> 1,446,280 bytes. (The "custom framing" worry was wrong for these; standard headered LZMA.)
- Carved 143 files via `&*#@name@#*&len` markers -> analysis/extracted/files/ (120 htm,17 js,6 css).
  = the COMPLETE Topnet web admin UI (FR/EN). 106+ pages. See analysis/firmware-extracted.md.
- Web engine = Realtek VWS (pages use <VWS_FUNCTION>/<VWS_SCREEN>; live values server-side, so no
  plaintext creds in static HTML). CSRF token via SendKeyCSRF().
- VULN SURFACE (candidates, analysis/vuln-assessment.md) - NOT yet confirmed (handler code is in
  the upper 12MB we can't reach via tftpbk):
  * C1 HIGH: cmd injection in form2ping.cgi / form2traceroute.cgi (free-text ipaddr, client-side
    validation only). Classic Realtek bug. Confirm via binary (sprintf+system) or LIVE POST
    ipaddr=127.0.0.1;telnetd on the booted router.
  * C2 HIGH: upload.htm/autoboot.htm/replaceboot.htm firmware+boot write; SecureVerify DISABLED.
  * C3 MED: login.cgi/CSRF token/session strength. C4: debug.htm (Sardebug/portmirror), ledtest.
  * C5: default web creds live in config block (decompress it) / boot log has WiFi creds.
  * C6: TR-069 ACS acs3.topnet.tn:1111, CWMP 7547 open to Topnet 41.226.15.248/29.
- LIMIT: decompressed 4MB = web resources, NOT compiled CGI handlers. To CONFIRM vulns:
  chip-off GD25Q128 (CH341A, 3.3V NOR, no adapter) -> full 16MB -> Ghidra (MIPS BE/Lexra) ->
  trace ipaddr->system; OR live POST test on own device.
- NEXT: (a) chip-off for full 16MB + Ghidra; (b) decompress config block (FORMAT_ALONE on its
  LZMA payload) for plaintext MIB/creds; (c) live cmd-injection test on form2ping.cgi.

## 2026-10-10 (session 1e) — CHIP-OFF success; flash is 4MB not 16MB (full firmware confirmed)
- In-circuit clip kept browning out the CH341A (board load). DESOLDERED the flash (normal iron)
  and read the LOOSE chip -> no brown-out -> clean read. (CH341A 5V-flaw noted for future; here
  it read fine. For the 1.8V S20 NAND still need a 1.8V adapter.)
- flashrom: `Found GigaDevice flash chip "GD25Q32(B)" (4096 kB, SPI)`. Read + verify, matching MD5.
  -> firmware/gd25q32_dump.bin == firmware/flash_full_chipoff_4MB.bin (809ba341..., 4194304 B).
- KEY CORRECTION: flash is **4 MB (GD25Q32)**, NOT 16 MB. Bootloader "Flash Size:16M" was wrong.
  So tftpbk's 4MB "wall" = the whole chip; `d 0xC0000000` hung = past end. NO upper 12MB exists.
  The earlier TFTP dump was ALREADY the complete firmware. Chip-off == TFTP dump byte-for-byte
  except last 32B at 0x3FFFE0 (config checksum tail: TFTP 00 vs chip-off FF).
- => We have the COMPLETE firmware (confirmed two independent ways). Everything extracted in
  session 1d (143 files, web UI) is the full picture. First successful chip-off. 
- NOTE: this chip is the Topnet RTL8676S router's flash (user confirmed 'the RTL').
- NEXT: full RE of the app code is still limited (the 4MB is loader + LZMA web resources +
  erased space; the compiled CGI handlers appear packed in the app blocks 0x40000-0x200000 ->
  decompressed into all_decompressed.bin). For vuln confirmation: disassemble all_decompressed.bin
  in Ghidra (MIPS BE/Lexra) to find form2ping/login handlers; or live POST test on the router.

## 2026-10-10 (session 1f) — config DECODED + CLI access + full device ID
- Cracked the SW config block: raw LZMA1 (lc0/lp0/pb0) at header+13, max_len 39158 -> XML
  <Config_Information_File_8671>. All accounts recovered -> analysis/config-decoded.md:
  admin/admin (right 0x3), useradmin/useradmin, user/user, topadmin/[REDACTED_PW],
  superadmin/[REDACTED_SUPERADMIN_PW] (top), owner [REDACTED_EMAIL]. WiFi PSK [REDACTED_WIFI_PSK]. PPPoE
  user tp-[REDACTED_SERIAL]@topnet.tn. (Reusable trick: vendor "encrypted" config = raw LZMA; sweep
  offset+props vs known output size.)
- Logged into the device CLI (ADSL# prompt) via UART/telnet. Captured a session ->
  captures/cli-session-raw.txt; distilled -> notes/cli-reference.md.
- AUTHORITATIVE device ID (show version): Model **TOPNET ADSL Router TD8963N**, mfr TP-Link
  (OUI [REDACTED_OUI]), FW V7.0421.01, SDK V1.3.1, HW 8671x, Serial [REDACTED_SERIAL], MAC [REDACTED_MAC].
- AUTHORITATIVE flash layout (system show flashlayout): 4MB total 0xBFC00000-0xC0000000; run image
  0xBFC10000; HW cfg 0xBFC04000(8K); config 0xBFFFC000(16K); BACKUP config 0xBFFF8000(16K, not
  yet dumped); file area 0xBFFF0000(32K); unused 0xBFE20000-0xBFFF0000 (1856K). Confirms 4MB, no 16MB.
- 36 RTOS tasks enumerated (system show task); services open per nmap: 21 ftp,23 telnet,53 dns,
  80 http,443 https,7547 cwmp (161 snmp & 8080 closed).
- SCOPE: own retired device. We will NOT use recovered ISP creds (superadmin / ACS) against
  Topnet infrastructure or other subscribers — local study only.
- NEXT (read-only completeness): show cwmp/interface/ip/processes/command/web; cfgmib; xfile;
  dump backup config @0xBFFF8000 + file area @0xBFFF0000; try `sh`/`quit` for a lower shell.

## 2026-10-10 (session 1g) — started live web pen-test; planned responsible disclosure
- Began Phase 1 (unauthenticated) web testing on 192.168.1.1 (own device, LAN). Finding so far:
  EVERY path returns HTTP 200, even fake filenames -> 200 is meaningless (server serves login
  body with 200, no 401/403). INCONCLUSIVE; must compare response BODIES next (real protected page
  vs a fake page) to tell auth-enforced vs auth-bypass vs pre-auth disclosure. See
  analysis/vuln-assessment.md "Live web pen-test" for the exact next command + decision tree.
- Discussed bug bounty / disclosure: scope to OWN device only; never touch Topnet infra or other
  subscribers. Likely report to TP-Link PSIRT (+ Topnet). Redact creds/serial before publishing.
  Research known SDK defaults + CVEs next to judge novelty/severity.
- STATE: project fully documented. Pen-test paused mid Phase-1 (resume at the body-compare step).

## RESUME HERE next session
1. Web pen-test Phase 1: run the body-compare curl (vuln-assessment.md) -> classify auth.
2. Then Phase 2/3 (user, then admin creds) -> hunt cmd-injection in form2ping.cgi / auth bypass.
3. Read-only CLI completeness: show cwmp/interface/command/web, cfgmib, xfile; dump backup config
   @0xBFFF8000 + file area @0xBFFF0000.
4. Research RTL867x/TD8963N known defaults+CVEs; draft redacted disclosure report.

## data wanted (hand these to the AI when you can)
- Full UART boot log (power-on to idle) at 115200.
- Loader outputs: `bootline`, `mac`, `memsize`, `flashsize` (just reading, no writes).
- Board photos: whole board both sides + close-ups of SoC, flash, RAM, WLAN/PHY chips, UART pads.
- Any label text: model name, S/N, FCC/TELEC, Topnet branding.
- Full 16MB flash dump.
