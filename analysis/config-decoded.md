# Decoded config (SW config block) — RTL8676S Topnet router

Owner's own device. Config recovered by decompressing the SW config block from the flash dump.

## How it was decoded
- SW config @ flash 0x3FC000 (0xBFFFC000), 16 KB. Header (16 B) then a RAW LZMA1 stream.
- Header: `00 00 1B 2A 06 D1 30 65 00 00 40 00 00 00 1E 12` (0x1B2A=6954=compressed len = boot log
  preLen; unPreLen 39158). Payload starts at header offset **+13**.
- Decompress: Python lzma FORMAT_RAW, filter LZMA1 lc=0 lp=0 pb=0, dict 8MB, on region[13:],
  max_length 39158. -> 39158 bytes of XML `<Config_Information_File_8671>`.
- Output: analysis/extracted/sw_config_decompressed.bin (XML, `<V N="NAME" V="VALUE"/>` entries).
  (This is the Realtek config codec; standard .lzma header absent -> raw stream, props lc0/lp0/pb0.)

## Login accounts (user table)
| Username                  | Password            | Right |
|---------------------------|---------------------|-------|
| admin                     | admin               | 0x3 (full admin) |
| useradmin                 | useradmin           | 0x2   |
| user                      | user                | 0x1   |
| topadmin                  | [REDACTED_PW]    | ISP   |
| superadmin                | [REDACTED_SUPERADMIN_PW]        | highest/ISP |
| [REDACTED_EMAIL]   | [REDACTED_PW]    | owner account |

Observations:
- admin/useradmin/user left at DEFAULT creds (username==password). superadmin/topadmin are
  ISP-set hidden accounts (not in the normal UI) with stronger/unique passwords.
- UIF_PW_REQUIRED=0x0. TELNET_STATE=0x0 (off), TELNET_PORT=0x17(23). NAT_WANACCESS=0x0.

## Other settings of interest
- WiFi: WLAN_WPA_PSK = [REDACTED_WIFI_PSK] ; WLAN_WSC_PSK = [REDACTED_WIFI_PSK] ; SSID [REDACTED_SSID] (boot log).
- WAN PPPoE: PPPUSER = tp-[REDACTED_SERIAL]@topnet.tn (PPP password elsewhere in config block).
- TR-069: CWMP_SERVER_USER=[REDACTED_OUI]---[REDACTED_SERIAL] ; CWMP_CONREQ_USER=[REDACTED_SERIAL] ;
  ACS http://acs3.topnet.tn:1111/ACS-INTF ; CWMP_PARAMETERKEY=unsetCommandKey.
- Config format = XML, root <Config_Information_File_8671>, flat <V N= V=> list (Realtek MIB dump).

## Use
- Web admin 192.168.1.1: admin/admin (full). superadmin/[REDACTED_SUPERADMIN_PW] = top privilege.
- Full decoded XML: analysis/extracted/sw_config_decompressed.bin.
