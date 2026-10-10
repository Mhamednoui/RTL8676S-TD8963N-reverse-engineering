# Firmware extraction — SUCCESS (web UI + app from first 4 MB)

## Result
The compressed app region (flash 0x40000-0x3C000+) is a series of **134 standard .lzma streams**
(props 0x5D = lc3/lp0/pb2, 8MB dict), concatenated. Decompressed with Python
`lzma.FORMAT_ALONE` -> **1,446,280 bytes** of firmware content, **106 web pages**, JS/CSS, app data.
(Earlier "custom framing" conclusion was WRONG for these streams — they're standard headered LZMA;
binwalk located them and read their uncompressed sizes. Only the raw-at-start guess failed.)

Reproduce: `py scripts/extract_lzma_streams.py firmware/flash_first4mb.bin analysis/binwalk_results.txt analysis/extracted`
Outputs in analysis/extracted/: streams/ (134 files), all_decompressed.bin, strings_all.txt, pages.txt.

## Stream layout (from binwalk)
- 0x8020  : 70040 B uncompressed  -> first big block (app code/data)
- 0x10040 .. ~0x3688D : many ~32 KB blocks -> paged app image (code + resources)
- 0x37DC6 onward : many small streams (184 B .. 5 KB) -> individual files (htm/js/css/text)

## What's inside (confirmed)
- **Full web admin UI** (Topnet-branded, FR+EN). 106 .htm pages, incl:
  index, login, status, wan, wanatm, adslconfig/adslset (ADSL), wlbasic/wlwpa/wlwps/wlmbssid
  (WiFi), tr069 (CWMP/ACS), telnet_onoff, debug, autoboot/replaceboot (bootloader control!),
  userconfig/modify_hide (users), snmp, ddns, ftpd, dmz/nat/virtualSrv/portmap (firewall),
  ipqos, upnp, logging, reboot/rebootdefault, saveconf, upload (firmware update), ledtest,
  oamloopback (ADSL OAM), diag, ping/traceroute (+ _v6 variants).
- **JS/CSS**: adminMenu.js, init.js, internetlist.js, juicer.js (0.4.0-dev templating),
  jquip.js/jquip_sizzle.js (jQuery-like), base.css. Files are delimited in-image by
  markers `&*#@<filename>@#*&<len>`.
- Web engine: Realtek "VWS" server -> pages use `<VWS_FUNCTION ...>` / `<VWS_SCREEN ...>` tags
  that the RTOS fills at serve time (so live values like passwords are NOT in the static HTML;
  they come from the config/runtime). CSRF via SendKeyCSRF().
- (c)Copyright Realtek, Inc. 2012. App = OSK RTOS image. Firmware V7.0421.01 (2021-04-14).

## Security-relevant pages to study next (Ghidra/RE of the app binary)
- login.htm / userconfig.htm / modify_hide.htm -> auth flow, default creds (values in config).
- telnet_onoff.htm, debug.htm -> enabling telnet/debug (maps to app handlers).
- autoboot.htm, replaceboot.htm, upload.htm -> bootloader/firmware write paths.
- tr069.htm -> ACS creds (acs3.topnet.tn), ConnectionRequest auth.
- Note: the *values* (passwords, PSK, ACS pass) live in the LZMA config block (0xBFFFC000) and
  are also printed in the boot log (SSID [REDACTED_SSID], WPA [REDACTED_WIFI_PSK]) -> notes/findings-from-bootlog.md.

## Still TODO
- [ ] Decompress the CONFIG block the same way (it's also LZMA; try FORMAT_ALONE on sw_config
      payload at the right offset) -> plaintext MIB with all settings.
- [ ] Carve named files (split all_decompressed.bin on `&*#@name@#*&len`) into a browsable tree.
- [ ] Disassemble the app code blocks in Ghidra (MIPS/Lexra, big-endian) -> find auth check,
      telnet enable, any hardcoded creds/keys.
- [ ] Full 16MB via chip-off to get kernel/second-bank/calibration (upper 12MB).
