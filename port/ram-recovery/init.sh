#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /dev/pts /dev/socket /dev/usb-ffs/adb /run /tmp /data/misc/adb /data/adb /home/phablet /var/log
mount -t devpts devpts /dev/pts
mount -t tmpfs -o mode=0755 tmpfs /run
mount -t tmpfs -o mode=1777 tmpfs /tmp
: > /run/a05bd-ram-recovery
exec 9>/dev/watchdog0
[ ! -e /proc/wdk ] || printf '1 30\n' > /proc/wdk
( while :; do printf . >&9; sleep 2; done ) &
ln -s /proc/self/fd /dev/fd
ln -s /proc/self/fd/0 /dev/stdin
ln -s /proc/self/fd/1 /dev/stdout
ln -s /proc/self/fd/2 /dev/stderr
mount -t configfs configfs /sys/kernel/config
G=/sys/kernel/config/usb_gadget/a05bd_ut
mkdir -p "$G"
printf 0x18d1 > "$G/idVendor"
printf 0x4ee2 > "$G/idProduct"
printf 0x0200 > "$G/bcdUSB"
printf 0xef > "$G/bDeviceClass"
printf 0x02 > "$G/bDeviceSubClass"
printf 0x01 > "$G/bDeviceProtocol"
mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409" "$G/functions/acm.usb0" "$G/functions/ffs.adb"
printf a05bd-ut > "$G/strings/0x409/serialnumber"
printf UBports-recovery > "$G/strings/0x409/manufacturer"
printf A05BD-RAM-recovery > "$G/strings/0x409/product"
printf RAM-recovery > "$G/configs/c.1/strings/0x409/configuration"
printf 250 > "$G/configs/c.1/MaxPower"
ln -s "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0"
ln -s "$G/functions/ffs.adb" "$G/configs/c.1/ffs.adb"
mount -t functionfs -o uid=32011,gid=32011,mode=0770 adb /dev/usb-ffs/adb
chown -R 32011:32011 /data /home/phablet /var/log
/usr/bin/adbd-launch > /run/adbd.log 2>&1 &
sleep 3
for U in /sys/class/udc/*; do [ -e "$U" ] || continue; printf '%s' "${U##*/}" > "$G/UDC"; break; done
while [ ! -c /dev/ttyGS0 ]; do sleep 1; done
exec </dev/ttyGS0 >/dev/ttyGS0 2>&1
stty -F /dev/ttyGS0 -ixon -ixoff -ixany 2>/dev/null
printf '\nA05BD_RAM_RECOVERY_READY\n'
# All internal filesystems intentionally remain unmounted. No automatic writes/fsck.
cat /proc/mounts
while :; do /bin/sh -i; done
