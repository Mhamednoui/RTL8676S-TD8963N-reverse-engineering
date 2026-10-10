# Findings extracted from the full boot log (captures/boot.log)

Everything here is read straight from the device's own boot output. Owner's own router.

## Hardware (confirmed)
- SoC: RTL8676S ("8676S ctrlin readback", "867x ver = Q", gSocId=0x63330000, AFE_ver 0x3430).
  Core: Realtek Lexra (MIPS-like), big-endian.
- Integrated LAN/NIC: **RTL8196B** ("Probing RTL8186 10/100 NIC... chip name: 8196B revid 0").
- WLAN: **RTL8192E** (2.4GHz; "RTL8192E_MAC_PHY_Parameter..."), driver v3.6.3 (2017-08-23);
  also string "eric-8822"/RTL8822 references (possible 5GHz/2nd radio or shared param set).
  WLAN MAC base [REDACTED_MAC] (+..91..94 for vaps). Realtek OUI [REDACTED_OUI].
- RAM: DDR via "6256/6257" controller ("8676(>M) + 6256/6257 decide use DDR mode"); size TBD.
- Flash: GigaDevice SPI NOR, boot log shows short id "c8/40". (Chip-off later confirmed the actual
  part is **GD25Q32, 4 MB** — the bootloader's reported "16M" was wrong. See device-profile.md.)
- DSL: ADSL/VDSL modem (ATM PVCs, adslCfgMode modemask=0xff). Default PVC vpi=0 vci=35 PPPoE;
  mgmt PVCs vpi=0/vci=16 and vpi=1/vci=39.

## Firmware / OS
- Firmware V7.0421.01, build Apr 14 2021. Bootloader RTL867X LOADER (LZMA) 00.01.02a-rc 2018.
- RTOS "OSK" (not Linux). Tasks: CFGTASK, CLITASK, XTCPIP, SNMP, PPPoE/ppp, Telnet, DHCP, UPNP,
  CWMPSRV/CWMPCLT/CWMPDL (TR-069), WSC, dhcpv6c/d, pptp-client, l2tp, BFTPD/FTPC, NTP, DDNS...
- Config system = "MIB chains" (named records). Loader decompresses config (LZMA) at boot.
  Many "descpritor's size don't match its recordSize" warnings (version mismatch vs defaults,
  benign) + "loadDefaultSetting" -> this unit fell back to some default settings.

## Network / config (plaintext, from boot log)
- WiFi SSID: **[REDACTED_SSID]**
- WiFi security: WPA2-PSK (authtype/encmode -> psk_enable=3, wpa2_cipher=10/CCMP)
  **WPA passphrase/PSK: [REDACTED_WIFI_PSK]**  (also used as WSC PSK; 802.1x WPA daemon)
- WiFi: single root wlan0 + 4 vaps (vap0-3, disabled), regdomain=3, band=11 (bgn), channel auto.
- LAN: 192.168.1.1/24 (0xc0a80101 / 0xffffff00).
- WAN: PPPoE over ATM (vpi0/vci35), NAT enabled on itf 15.
- TR-069 / CWMP: ACS **http://acs3.topnet.tn:1111/ACS-INTF**, CWMP port 7547.
  WAN->local ACL permits TCP from **41.226.15.248/29** to port 7547 (Topnet mgmt subnet).
  Also RIP udp 520 permitted. InformInterval 86400s. cwmp delay start 30s.
- Remote mgmt PVCs: vpi0/vci16 (wan_no 18), vpi1/vci39 (wan_no 19) "out of band channel".
- IPv6 enabled (Ipv6 Lib 8.0.0), ip6 firewall rules set.

## Boot-ROM / download mode (the early garbled part)
- "USB-SN / NOLINK / TAND / flag bypass" then a burst of binary (the loader image being pulled),
  then "Start to decompress!", "Press 'ESC' to enter BOOT console", "Boot from NOR/SPI flash".
- "Ext. phy is not found" -> uses internal PHY (matches info MII sel 0).

## Addresses / map (confirmed)
- Flash window 0xBFC00000 (uncached). HW cfg 0xBFC04000 (8KB). SW cfg 0xBFFFC000 (16KB).
- eraseUnusedFlash region 0xBFE20000..0xBFFF0000.
- RAM exec region 0x8000_0000+; task stacks ~0x5000_0000 (uncached data pool).
- Loader: Load/Entry 0x80000000, App 0x9FC10000.

## Security observations (for the writeup)
- WPA PSK + ACS URL + mgmt ACL printed in cleartext on the console = anyone with UART sees creds.
- CWMP reachable from the ISP mgmt subnet (41.226.15.248/29) on 7547 -> ISP can remote-manage.
- "ecb(arc4) init failed!" and sha1 crypto register -> crypto present (TLS for ACS, WPA).
