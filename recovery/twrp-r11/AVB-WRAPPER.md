# Tested R11 recovery wrapper

Raw image SHA256 cae9483c779cc994bd100e58637b38bddaf38403bf53559c26fca9bd556c8c69.
The installed/tested variant preserves this full raw image prefix and adds a
16MiB AVB hash footer using the pinned external/avb/avbtool (Python2, avbtool1.1.0):

```
avbtool add_hash_footer --image recovery.img --partition_size 16777216 \
  --partition_name recovery --algorithm NONE \
  --salt c6c2eab2c241aa0713e6cf5ed63bc0728b9ea860c506ed3b81b555ee20da3351
avbtool verify_image --image recovery.img
```

Footer original size16115712, VBMeta offset16117760, size512. Wrapped image SHA256
047ae969f79adc7bfd290e79da76985f2db3e74b58702b507bcce34e66406928.
Algorithm NONE provides hash metadata, not authentication. Target is already
unlocked with the port's existing vbmeta configuration. No keys are used.
The verification filename must be recovery.img (hash descriptor partition name).
The wrapper being required by the bootloader has not been proven: the initial
fastboot reboot recovery attempts actually returned to normal Ubuntu mode0.
A real recovery boot via systemd reboot-param recovery succeeded in mode2,
with automatic ADB and the exact wrapped recovery partition SHA.
