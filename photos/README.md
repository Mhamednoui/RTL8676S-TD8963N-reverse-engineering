# Photos

Hardware + console photos from the reverse-engineering sessions. All shots are of the
owner's own, de-provisioned (dead line) TD8963N. Personal/identifying fields (serial
number stickers, device MAC) are masked out in the images.

| File | What it shows |
|------|---------------|
| `board-uart-flash.jpg` | The PCB with the 4-pin **UART header** and the **GigaDevice GD25Q32** SPI-NOR flash annotated. |
| `bench-setup.jpg` | The bench: CH341A SPI programmer + SOIC-8 clip, CP2102 USB-TTL serial adapter, multimeter probes, board open. |
| `bootloader-help.jpg` | The **RTL8676S LOADER (LZMA)** banner (v00.01.02a-rc) and the `<RTL867X>` boot-console `help` command list (tftp/tftpbk/r/w/d/flashsize/...). Reached by pressing **ESC** at power-on. |
| `cli-login-and-help.jpg` | The `ADSL#` runtime CLI login and top-level `help` (config / debug / diagnostic / sh / show / reboot). |
| `cli-show-system-status.jpg` | `show system status` — model **ADSL Router TD8963N**, firmware **V7.0421.01** (build Apr 14 2021), uptime. (MAC + a label field masked.) |

See `../notes/uart-and-dumping.md` and `../notes/device-profile.md` for the full method
behind each shot.
