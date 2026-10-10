# Vulnerability assessment — RTL8676S Topnet CPE (firmware V7.0421.01)

Own device, retired. This is a CANDIDATE list from the extracted web UI (143 files carved to
analysis/extracted/files/). Client-side only shows the ATTACK SURFACE; exploitability is decided
by the CGI handlers in the app binary -> needs Ghidra disassembly to CONFIRM. Nothing here is a
verified exploit yet; each item says what to check next.

## Method so far
- Firmware app = 134 LZMA streams -> decompressed (scripts/extract_lzma_streams.py) -> carved into
  143 files (120 .htm, 17 .js, 6 .css) via the `&*#@name@#*&len` markers.
- Grepped for creds, injection, auth, CSRF. No plaintext passwords in static HTML (server-side
  via VWS_FUNCTION/VWS_SCREEN). CSRF token present (SendKeyCSRF()).

## CANDIDATE findings (ranked by likely impact)

### C1 — Command injection via diagnostic CGIs  [HIGH, most promising]
User-supplied host/IP fields passed to network tools. Classic Realtek RTL8xxx bug class.
- ping.htm       -> POST form2ping.cgi      field `ipaddr` (text, maxlen 40)
- traceroute.htm -> POST form2traceroute.cgi field `ipaddr` (text, maxlen 30) + numeric fields
- form2pingv6.cgi, form2traceroute6.cgi (v6 variants)
- diag-test.htm  -> formDiagTest.cgi ; adsl-diag -> formDiagAdsl.cgi ; oam -> form2oam.cgi
- Client validation is weak/regex-only (validateKey on numbers; ipaddr largely unchecked).
- CHECK NEXT: in the app binary, does form2ping/form2traceroute build a shell string with the
  ipaddr (e.g. sprintf("ping %s", ipaddr) -> system/popen)? If unsanitized -> inject with
  `;`/`|`/backtick/`$()`. maxlength is client-side only (bypass via direct POST).
- TEST (own device, when powered): POST ipaddr=`127.0.0.1;telnetd` etc. to form2ping.cgi.

### C2 — Firmware/bootloader upload paths  [HIGH if auth weak]
- upload.htm (firmware image), autoboot.htm / replaceboot.htm (boot loader), saveconf.htm/
  form2saveConf.cgi (config). File inputs: "download boot file", "download image file".
- CHECK NEXT: is there auth + image signature/magic validation before write? SecureVerify was
  DISABLED (boot log) -> a crafted image likely boots -> persistent implant path.

### C3 — Auth / session strength  [MEDIUM]
- login.htm -> login.cgi. userconfig.htm/formModify.cgi, modify_hide.htm manage users.
- CSRF token via SendKeyCSRF() (adminMenu.js/init.js) -> check token generation (Realtek tokens
  have been predictable/static before). Check session cookie entropy + whether pages enforce auth
  server-side (some Realtek CPEs let you GET a page or hit a cgi without a valid session).
- modify_hide.htm name suggests "hidden" admin fields -> inspect.

### C4 — Exposed debug/engineering pages  [MEDIUM/INFO]
- debug.htm (Sardebug & Portmirror), ledtest.htm, diag-test.htm, form2file*.cgi present in
  shipped firmware. CHECK: reachable pre-auth? what do Sardebug/portmirror expose?

### C5 — Default credentials  [unknown -> check config/binary]
- Not in static HTML. Live values in the LZMA config block + printed in boot log:
  WiFi SSID [REDACTED_SSID] / WPA2 [REDACTED_WIFI_PSK]. Admin web pw lives in config -> decompress config
  block or find default in the binary (strings like "admin"/"user" near login.cgi handler).

### C6 — TR-069 / ACS exposure  [INFO, by design]
- tr069.htm; ACS http://acs3.topnet.tn:1111/ACS-INTF; CWMP 7547 reachable from Topnet mgmt
  subnet 41.226.15.248/29 (boot-log ACL). ISP can remote-manage/flash. ConnectionRequest creds
  in config. Not a "vuln" per se but a remote control surface.

## Full CGI endpoint inventory (from carved pages)
login.cgi, formModify.cgi, form2userconfig.cgi, form2ping.cgi, form2pingv6.cgi,
form2traceroute.cgi, form2traceroute6.cgi, formDiagTest.cgi, formDiagAdsl.cgi, form2oam.cgi,
form2saveConf.cgi, form2WanAdsl.cgi, form2portmap.cgi, form2natpass.cgi, form2natmappingdel.cgi,
form2url.cgi, form2WlAc.cgi, form2IPQoS.cgi, form2IPQoSTc.cgi, form2PortriggerRule.cgi,
form2filterfwd.cgi, form2Acldel.cgi, formIpRange.cgi, form2timelimit*.cgi, form2systime.cgi,
form2ntp.cgi, form2ntpstart.cgi, form2stf.cgi, ... (see grep output / files/)

## Live web pen-test — in progress (own device, LAN)
Methodology: unauthenticated -> low-priv (user) -> admin -> hunt injection/bypass.

### Phase 1 (unauthenticated) — STARTED, INCONCLUSIVE so far
- `curl` (no cookie) to many pages ALL returned HTTP 200 — INCLUDING guessed/fake filenames
  (config.xml, romfile.cfg, backupsettings.conf). => 200 alone is meaningless here; the server
  likely serves the login page body with a 200 for everything (no proper 401/403/302).
- NEXT (unfinished): compare RESPONSE BODIES/sizes of a real protected page (userconfig.htm) vs
  a FAKE page (notareal_page_xyz.htm). Command staged:
    for p in status.htm userconfig.htm tr069.htm config.xml romfile.cfg notareal_page_xyz.htm; do
      echo "== $p =="; curl -s http://192.168.1.1/$p | head -c 300; echo; done
  * If fake == real == login page -> auth is ENFORCED (200 is just the login redirect body).
  * If userconfig.htm shows real admin content but fake shows login -> AUTH BYPASS (vuln).
  * If config.xml/romfile.cfg returns real config -> PRE-AUTH DISCLOSURE (big vuln).
- Known creds (from decoded config) for the authed phases: admin/admin, user/user, superadmin/
  [REDACTED_SUPERADMIN_PW]. Web UI at 192.168.1.1; also telnet 23, ftp 21 open.

### Remote-attacker reality (for any disclosure)
Everything we exploited needed physical (UART/chip-off) or LAN+creds. A remote attacker only has
the WAN side: TR-069/CWMP 7547 (open to Topnet mgmt 41.226.15.248/29) + whatever is WAN-exposed.
The systemic, reportable issues are: (a) DEFAULT creds admin/admin, user/user (fleet-wide if same
on all TD8963N units); (b) HIDDEN superadmin/topadmin accounts — severity depends on whether their
passwords are device-unique or operator-wide (unknown without a 2nd unit — report as a concern,
do NOT test other devices); (c) secure-boot disabled; (d) candidate cmd-injection in diag CGIs.

## Responsible disclosure (planned, legitimate)
- Report scoped to OWN device only. Do NOT scan/access Topnet infra or other customers' routers.
- Contacts: TP-Link PSIRT (security@tp-link.com / their security page) — real coordinated-
  disclosure program; Topnet security/abuse (security@topnet.tn if it exists). Bug bounty: Topnet
  likely none; TP-Link limited/none for EOL CPE -> do it for CVE/credit, not money.
- REDACT before any public step: WPA key, serial [REDACTED_SERIAL], PPPoE login, superadmin/ACS pwds.
- TODO: research whether these creds are known Realtek/TP-Link SDK defaults + known CVEs for
  RTL867x/TD8963N (web, no illegal testing) -> decides novelty + severity; then draft the report.

## To CONFIRM any of these (next real step)
1. Disassemble the app code blocks in Ghidra (big-endian MIPS/Lexra). The first big LZMA block
   (0x8020, 70KB) + the ~32KB paged blocks are the code; locate the httpd/VWS cgi dispatch table
   and the form2ping/form2traceroute/login handlers.
2. Trace the ipaddr field from form2ping.cgi to any system()/popen()/exec -> confirm C1.
3. Check login.cgi for default creds / auth-bypass and the CSRF token generator.
4. (Live, own device) replay crafted POSTs to the cgis to validate.

## Known-CVE shortcut
This is a Realtek RTL819x/RTL8676 "OSK/Jungle" SDK CPE (2021). The family has public CVEs for
command injection in diag/ping, auth bypass, and info leak. Cross-reference the exact cgi names
above against published Realtek CPE advisories before deep RE.
