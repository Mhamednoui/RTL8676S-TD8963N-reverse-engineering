# UART access + flash dumping — RTL8676S

## UART wiring (CONFIRMED)
4 pads on the board: GND, TX, RX, VCC. Logic level **3.3V** (CP2102 connects directly).
```
Router TX  ──► CP2102 RXD      (read console)
Router RX  ◄── CP2102 TXD      (send keys, e.g. ESC)  -- the pad that SAGGED under 330R load
Router GND ─── CP2102 GND
Router VCC ─── leave UNCONNECTED (the 3.3V pad that HELD under load)
```
Baud **115200**, 8N1, no flow control.

### How the pins were identified (method, reusable)
- GND: continuity (~0) to metal shield / DC-jack barrel.
- TX: idles 3.3V, voltage DROPS/flickers in first seconds of boot (data out).
- RX vs VCC (both idle 3.3V): LOAD-SAG test — with router ON and meter in DC volts (black on
  GND), briefly bridge each pad to GND through ~330Ohm:
    * VCC holds ~3.3V (stiff supply)   -> do NOT connect
    * RX collapses to ~0V (weak pull-up input) -> this is RX

## Terminal
Kali: `sudo picocom -b 115200 /dev/ttyUSB0`
Log to file: add `-g ~/name.log`  (toggle in-session: Ctrl-A Ctrl-G). Exit: Ctrl-A Ctrl-X.
If garbage: wrong baud — try 57600 / 921600. (This device's console is a steady 115200.)

## Entering the boot loader
Power-cycle the router and **spam/hold ESC** in the first ~1-2s. Prompt: `<RTL867X>`.

## Boot loader command reference (RTL867X LOADER)
- `info`                      device/flash/mem summary
- `bootline`                  boot line / env
- `mac [...]`                 read/set MAC (read only!)
- `r [addr]`                  read ONE word at addr
- `d [addr] <len>`            DUMP <len> bytes as hex (our read path)
- `w [addr] [val]`            write word  -- DANGEROUS, do not use
- `load [address]`            load image to RAM
- `run [app] [entry]`         execute
- `xmodem [address]`          xmodem transfer (binary, serial)
- `tftp [ip] [srvip] [file]`  tftp get
- `tftpbk [size] [clientip] [serverip] [file]`  TFTP BACKUP = read flash -> send to TFTP server
- `flashsize`, `memsize`, `uart`, `entry`, `multicast`, `reboot`

## Memory map (MIPS/Lexra)
- kseg0 (cached)   0x80000000 -> phys 0x00000000  (RAM/exec)
- kseg1 (uncached) 0xA0000000 -> phys 0x00000000
- reset vector phys 0x1FC00000 -> **flash base 0xBFC00000** (uncached) / 0x9FC00000 (cached)
- To read flash via `d`, use the uncached window 0xBFC00000.

## Dumping the flash — 3 ways (prefer tftpbk)

### A) tftpbk over Ethernet (FAST, binary, lossless) — PREFERRED
Kali TFTP server:
```
sudo apt install -y tftpd-hpa
sudo mkdir -p /srv/tftp && sudo chmod 777 /srv/tftp
sudo systemctl restart tftpd-hpa
ip addr        # note Kali's IP on the router's LAN subnet
```
Connect router LAN -> Kali. Set/know the loader's client IP (bootline/`tftp` args). Then:
```
tftpbk 0x1000000 <router-ip> <kali-ip> flash_full.bin
```
0x1000000 = 16MB. File lands in /srv/tftp/flash_full.bin -> copy to firmware/.
(May need to configure the loader's IP first; check `bootline`.)

### B) `d` hex over serial (slow, ~30-60+ min for 16MB, fragile)
```
# picocom with logging on:
d 0xbfc00000 1000000
```
Then clean with scripts/rtl_clean.py (handles the 0xADDR: hex ascii format).
Risk: one dropped char corrupts that region; rtl_clean reports gaps (hexdump_to_bin.py version).

### C) xmodem (binary, error-checked, moderate speed)
`xmodem [address]` + picocom xmodem receive (Ctrl-A Ctrl-R). Good middle ground if TFTP networking
is awkward.

### D) Chip-off (always works)
GD25Q128 is SOIC-8 3.3V -> CH341A (3.3V, NO adapter needed for NOR) + SOIC-8 clip, flashrom/
NeoProgrammer. Use this if the board interface fails.

## Partial dumps already done
- SW config: `d 0xbfffc000 4000`  -> captures/sw_config.log -> dumps/sw_config.* (ENCRYPTED).
- HW config: `d 0xbfc04000 2000`  (TODO capture/clean).
