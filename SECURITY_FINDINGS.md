# Security findings — TOPNET TD8963N (Realtek RTL8676S)

**Educational / research write-up.** This documents weaknesses found while reverse-engineering
**my own, retired** Topnet TD8963N router (dead line, no active service) for learning. It is
published so others can learn how these device classes work and why these design choices are
risky. All real credentials, keys, serials and personal data are **redacted**. Nothing here was
tested against the ISP's network or anyone else's device, and nothing here should be.

> ⚠️ **Legal / ethical note.** Everything below was done on hardware I own. Doing any of this to a
> device, line or account that is not yours — or using credentials extracted from one device to
> connect as someone else — is illegal (unauthorized network access, service/identity theft,
> fraud) in Tunisia and essentially everywhere. This document exists to explain and help *fix*
> these weaknesses, not to exploit them. Use it only on equipment you own or are authorized to test.

---

## How the device was accessed (own hardware)
Physical only: UART serial console → the bootloader/RTOS CLI, and a chip-off read of the 4 MB
SPI-NOR flash with a programmer. From the dump, the compressed firmware and the configuration
block were decompressed offline. No remote exploitation was used or is described.

---

## Finding 1 — ISP broadband (PPPoE) password stored recoverably  [HIGH]

**What:** The subscriber's ISP broadband login — the PPPoE username and password used to
authenticate the line to the ISP — is stored in the device configuration and is recoverable from
a firmware/flash dump after decompression (the config block is LZMA-compressed, **not encrypted**).

```
PPPUSER   = tp-<SERIAL>@topnet.tn      (redacted)
PPPPASSWD = <REDACTED>
```
A factory/ISP-provisioned copy also appears (Realtek `HW_`-prefixed values live in the separate
hardware-config region), i.e. the broadband password exists in more than one place on the chip.

**Why it matters:** PPPoE authentication is just a username + password; the ISP's access server
grants and attributes the connection to whichever account those credentials match, with no strong
binding to a specific physical router. Therefore:
- Anyone with brief physical access to a customer's router (or a copy of its firmware image) can
  extract that customer's ISP credentials.
- If those credentials are accepted from other access points, the subscriber could be impersonated
  and **their** account billed and **their** name attributed to the resulting traffic.

**Root cause:** secrets stored with reversible compression rather than hardware-backed, non-
extractable storage; the broadband password is retrievable in cleartext once decompressed.

**Suggested mitigations (for the vendor/ISP):**
- Store line credentials in a secure element / OTP, not in readable flash.
- Bind sessions to a line/hardware identifier where the access network allows it.
- Rotate credentials that are known to have been exposed; treat a returned/retired CPE as a
  credential-exposure event.

---

## Finding 2 — Default and hidden administrative accounts  [HIGH]

**What:** The configuration contains several login accounts. Some ship with **default credentials
(username == password)**; others are **hidden ISP/engineering accounts** not shown in the normal
web UI, with higher privilege.

| Account (role)        | Credential            | Notes |
|-----------------------|-----------------------|-------|
| admin (full admin)    | default (user==pass)  | standard user-facing |
| useradmin             | default (user==pass)  | |
| user                  | default (user==pass)  | |
| topadmin (ISP)        | **REDACTED**          | hidden from normal UI |
| superadmin (highest)  | **REDACTED**          | hidden from normal UI, strong unique password |

**Why it matters:**
- **Default creds** mean a device left at factory settings is trivially accessible to anyone who
  can reach its admin interface.
- **Hidden higher-privilege accounts** are an opaque backdoor from the user's point of view: the
  owner cannot see or manage them, yet they grant more control than the owner's own account. If any
  such password is **shared across many units** (operator-wide rather than per-device), a single
  leak would affect the whole fleet. *(Whether it is shared cannot be determined from one unit, and
  must never be tested against other people's devices — it is noted here only as a concern.)*

**Suggested mitigations:** force a password change on first use; eliminate or disclose hidden
accounts; use strong, per-device passwords for any service account.

---

## Finding 3 — Secure boot disabled / firmware not signature-enforced  [MEDIUM]

**What:** The bootloader reports secure-verify disabled and skips the firmware signature check
("SecureVerify → Disable", "Skip Secure Verify" in the boot log).

**Why it matters:** modified firmware will boot. Combined with the writable update/boot paths in
the web UI, an attacker with admin access (see Finding 2) could install persistent, attacker-
controlled firmware.

**Suggested mitigation:** enforce signed-firmware verification in the bootloader.

---

## Finding 4 — Configuration obfuscated by compression, not protected  [MEDIUM]

**What:** The device configuration (credentials, keys, settings) is stored **LZMA-compressed**.
High entropy made it look encrypted, but it decompresses with standard tools once the framing is
identified — so it provides **no confidentiality**, only obscurity.

**Why it matters:** teams sometimes assume a high-entropy config blob is encrypted. It is not; all
secrets in it are recoverable. This is why Findings 1 and 2 are possible from a dump alone.

**Suggested mitigation:** encrypt sensitive config with a device-unique, hardware-protected key;
do not rely on compression for confidentiality.

---

## Finding 5 — Diagnostic web endpoints: unvalidated-input review needed  [INFO / candidate]

**What:** The extracted web UI includes diagnostic pages (ping, traceroute, diagnostic/OAM) that
submit a user-supplied host/IP field to the device. Client-side validation is minimal.

**Status:** **Not confirmed.** Whether the device-side handler safely validates these inputs
requires analysis of the compiled handler code; it is listed here only as an area a vendor should
review (classic class of issue in this device family). No exploitation was performed.

**Suggested mitigation:** strictly validate/escape any user input used to build a system command.

---

## Responsible disclosure

These are reported for defensive purposes. The appropriate path is private disclosure to the
vendor (TP-Link PSIRT) and the operator (Topnet), scoped to a device the researcher owns, with
sensitive values withheld from any public version. This document is the **redacted, educational**
version; it names no working secret.

## For learners
The point of publishing this is the *lessons*, not the credentials:
1. Consumer/ISP CPE often stores line and admin credentials recoverably in flash.
2. "Looks random" ≠ encrypted — compression produces high entropy too; always try to decompress.
3. Default and hidden accounts are common and are a real risk.
4. Physical access to a returned/retired router can expose a subscriber's ISP credentials — which
   is a reason to factory-reset and for ISPs to rotate credentials on returned equipment.
5. All of this is legal and useful **only** on your own hardware, for learning and disclosure.
