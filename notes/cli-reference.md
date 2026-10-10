# RTL8676S CLI (ADSL#) reference — live device enumeration

Accessed via UART serial console (or telnet) -> `ADSL#` prompt (Realtek RTL867x management CLI).
This is the RTOS management shell, NOT Unix (so `id`/`ls` fail). Raw session:
captures/cli-session-raw.txt. Key outputs distilled below.

## Device identity (from `show version` / `system show status`)  — AUTHORITATIVE
- Model: **TOPNET ADSL Router TD8963N**  (ManufacturerOUI [REDACTED_OUI], Manufacturer **TP-Link**)
- ProductClass: IGD ; Description: "ADSL SoHo Router"
- Application Version: **V7.0421.01**  (Build Apr 14 2021 10:28:23)
- SDK Version: **SDK V1.3.1**
- Hardware Version: **8671x**  (RTL8676S / RTL867x family, Lexra core)
- MAC: [REDACTED_MAC] ; Serial: [REDACTED_SERIAL] ; 14 ports
- Memory pool total 0xB2271C (~11.6MB usable of DRAM), free ~0x6ECEDC.

## Flash layout (from `system show flashlayout`) — AUTHORITATIVE, confirms 4MB
```
Flash Start        : 0xBFC00000   End 0xC0000000   Size 4 MB
Run Image Start    : 0xBFC10000
HW Config          : 0xBFC04000 - 0xBFC06000       8 KB
Config (main)      : 0xBFFFC000 - 0xC0000000       16 KB   <- the XML config we decoded
Backup Config      : 0xBFFF8000 - 0xBFFFC000       16 KB   <- NOT yet dumped (2nd copy!)
File area          : 0xBFFF0000 - 0xBFFF8000       32 KB
Unused             : 0xBFE20000 - 0xBFFF0000       1856 KB (erased)
Possible Max FW    : 4096000 bytes (4000 KB)
Defined  Max FW    : 4063232 bytes (3968 KB)
```
=> Confirms the chip is 4MB and there is NO 16MB. Note a BACKUP config at 0xBFFF8000 we haven't
   dumped yet (another copy of settings).

## Running tasks (from `system show task`) — 36 tasks, all Pri 4 "PEER"
Telnet=Run, XTCPIP/GENTSK/CLITASK/BFTPD=Ready/Run, rest Wait. Full list (stack base 0x50xxxxxx):
Phread1/Phread0 (PHY), IDLETSK, l2tp, pptp-client, dhcpv6c, dhcpv6d, WSC, auth_wlan, rtl8670
(WLAN, 0x2b2000 stack = largest), CWMPUE/DLD/DL/CLT/SRV (TR-069), UPNP, NTP, BFTPD, FTPC, DHCP,
Telnet, DDNS, SYSLOGD, DNS, TFTP, TFTPD, ppp, PPPoE, FEATTASK, SNMP, EWSTSK, XTCPIP, GENTSK,
CLITASK, STPMAIN, CFGTASK.

## Interrupts (`system show interrupt`)
irq08 timer0 ; irq13 ns16550 (UART) ; irq14 wlan0 ; irq15 (switch) ; irq18 dying gasp ;
irq24 <no name> ; irq25 sar (ADSL SAR).

## Top-level CLI command tree
- Enable/priv: `enable`, `login`, `disable` ; `configuration` (config mode).
- Diagnostics: `ping`, `ping6`, `trace`, `tracert6`, `tftp`, `adsl`, `ethstatus`.
- Debug: `debug`/`undebug`, `sardebug`, `ethdebug`, `sarmirror`, `capture`, `cpuocpy`, `swcore`.
- Config/flash: `cfgmib`, `flash`, `set`, `copy`, `script`, `html` (html simulate).
- System: `system`, `show` (big read-only tree), `reload`/`restart` (warm reboot), `logout`.
- Memory/FS: `memory`, `xfile` (DRAM file system), `xip`, `chksum`.
- `quit` / `sh` = "goto shell" / "enter shell mode" (try for a lower-level shell).

### `show` sub-tree (read-only enumeration)
adsl, arp, atm, clientlimit, command (full CLI tree dump), cwmp, dnscache, dos, ethernet,
fastpath, icmprt, interface, ip, ip6, logging, mac-address-table, macctl, memory, mib, mld,
ntp, oamf5, ppp, processes, qos, qos_db, snmp, socket, spanning-tree, status, system, tc, tcp,
twsfversion, url, urlredirect, version, vip, web (web page tree), wlan0 / wlan0-vap0..3 (WLAN MIB).

## TODO (read-only, for completeness)
- [ ] `show cwmp` (live ACS config), `show interface`, `show ip`, `show processes`
- [ ] `show command` (dump full CLI tree), `show web` (web page tree -> cross-check 143 files)
- [ ] `cfgmib` (live config MIB), `xfile` (DRAM fs listing)
- [ ] Dump the BACKUP config @0xBFFF8000 (16KB) + file area @0xBFFF0000 (32KB) via `d`/tftpbk
- [ ] Try `sh` / `quit` -> does it drop to a lower-level shell?
