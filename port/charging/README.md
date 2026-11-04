# A05BD power-off charging / 2026-11-04

Android9 charger built from the same pinned AOSP/TeamWin tree as TWRP R9.
`BOARD_CHARGER_ENABLE_SUSPEND=false`; `healthd_draw.cpp` changes blanking to
LCD backlight 0/102, keeping framebuffer scanout active. Kernel charger policy
and temperature/current limits are unchanged.

`a05bd-charger.target` replaces generic Android-container charger mode only for
boot mode 8/9 or explicit charger boot parameters. It runs the static charger,
watchdog and USB diagnostic console; Lomiri and the Android container stay off.
Normal reboot/PWRKEY boot continues to graphical.target.

Install resource assets by copying the existing device's `/android/res` into
`/usr/local/share/a05bd-charger/res`, then add animation.txt from the overlay.
The font is `charger/main_font`; without animation metadata upstream skips the
percentage field. The binary is installed at `/usr/local/sbin/a05bd-android-charger`.
Original binary inside android-rootfs.img is not overwritten.

Built charger SHA256: 944bff591872210e8a3efa6fcfd836b851ab3890baef4bdf416a315debc976df.
Watchdog SHA256: aa854a86d82b792eb1cc0bf768aefe959a07cf16082be583f039d9c0dbd98c90,
extracted from the verified R9 ramdisk; corresponding watchdog.c is included.
Build inputs: manifest-pinned.xml contains the exact upstream project revisions.
TWRP core commit 90e5d9559065cfa8b2b9a5dbb1c5cb7a88f034fa;
Android system/core commit 53782f5cc24fed4e332a0ac89b628f9ab17db0b4 (not necessarily the same
revision as the GSI's original charger).

Confirmed on device: boot mode 8 selected this target, charger and watchdog
active, backlight auto-off, serial console responsive, battery 94% to 95%,
charger RSS about 6MiB and 0.0% CPU while idle. The user confirmed visible percentage, timed blanking, short-press wake, and
long-press normal Ubuntu boot. Two off-mode boots and normal-boot regression passed.
Old RC3 releases do not yet include this fix. No new release was uploaded.
The /run mount is noexec: transfer payloads there, then install executables on
the real root filesystem before testing. Do not diagnose a failed /run execution
as a framebuffer or kernel crash.

Published with the RC4 / TWRP R11 / installer R2 release. See the top-level
INSTALL-TWRP.md and releases/rc4-20261104/report.md for the validated image path.
The stage-on-device and image build scripts are historical build inputs using
the original workspace paths, not an end-user installation command. The shipped
image includes the generator; the old staging helper alone does not enable it.
The complete system image was derived from public RC3 without copying user data.
