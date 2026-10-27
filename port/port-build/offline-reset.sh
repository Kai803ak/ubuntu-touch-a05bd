# SPDX-License-Identifier: GPL-3.0-only
# Sourced by Halium before userdata is bound into the new root.
a05bd_reset_contents() {
    # Caller validates the hardcoded mountpoint before calling this function.
    # A pending request is retained until ALL removals have succeeded.
    for a05bd_entry in "$1"/* "$1"/.[!.]* "$1"/..?*; do
        [ -e "$a05bd_entry" ] || [ -L "$a05bd_entry" ] || continue
        [ "$a05bd_entry" = "$1/.a05bd-factory-reset.request" ] && continue
        rm -rf -- "$a05bd_entry" || return 1
    done
}
a05bd_factory_reset() {
    a05bd_req=/tmpmnt/.a05bd-factory-reset.request
    [ -e "$a05bd_req" ] || [ -L "$a05bd_req" ] || return 0
    [ -f "$a05bd_req" ] && [ ! -L "$a05bd_req" ] || return 1
    [ "$(stat -c '%u:%a' "$a05bd_req")" = '0:600' ] || return 1
    [ "$(stat -c '%s' "$a05bd_req")" = 93 ] || return 1
    a05bd_line=$(cat "$a05bd_req")
    a05bd_nonce=${a05bd_line##* }
    [ "${#a05bd_nonce}" = 32 ] || return 1
    case "$a05bd_nonce" in *[!0-9a-f]*) return 1;; esac
    a05bd_uuid=${a05bd_line#A05BD_FACTORY_RESET_V2 }
    a05bd_uuid=${a05bd_uuid% *}
    case "$a05bd_uuid" in ????????-????-????-????-????????????) ;; *) return 1;; esac
    case "$a05bd_uuid" in *[!0-9a-f-]*) return 1;; esac
    [ "$a05bd_line" = "A05BD_FACTORY_RESET_V2 $a05bd_uuid $a05bd_nonce" ] || return 1
    [ "$_syspart" = /dev/mmcblk0p28 ] && [ "$file_layout" = partition ] || return 1
    [ ! -L /tmpmnt ] && [ ! -L /halium-system ] || return 1
    [ "$(cat /sys/class/block/mmcblk0p32/start)" = 15240192 ] || return 1
    [ "$(cat /sys/class/block/mmcblk0p32/size)" = 15295455 ] || return 1
    [ "$(blkid -s UUID -o value /dev/mmcblk0p32)" = "$a05bd_uuid" ] || return 1
    [ "$(blkid -s LABEL -o value /dev/mmcblk0p32)" = UTdata ] || return 1
    [ ! -e /tmpmnt/halium-rootfs ] || return 1
    awk '$1=="/dev/mmcblk0p32" && $2=="/tmpmnt" && $3=="ext4" {ok=1} END {exit !ok}' /proc/mounts || return 1
    awk '$1=="/dev/mmcblk0p28" && $2=="/halium-system" && $3=="ext4" {ok=1} END {exit !ok}' /proc/mounts || return 1
    awk '$2 ~ /^\/tmpmnt\// {bad=1} END {exit bad}' /proc/mounts || return 1
    [ -f /halium-system/var/lib/lxc/android/android-rootfs.img ] || return 1
    a05bd_state=/halium-system/var/lib/a05bd-reset
    [ ! -L "$a05bd_state" ] && [ -d "$a05bd_state" ] || return 1
    [ -f "$a05bd_state/pending" ] && [ ! -L "$a05bd_state/pending" ] || return 1
    [ "$(stat -c '%u:%a' "$a05bd_state/pending")" = '0:600' ] || return 1
    [ "$(cat "$a05bd_state/pending")" = "$a05bd_line" ] || return 1
    tell_kmsg 'A05BD factory reset: verified userdata, clearing offline'
    a05bd_reset_contents /tmpmnt || return 1
    sync
    # A power loss before unlink retries the same idempotent cleanup.
    rm -- "$a05bd_req" || return 1
    sync
    printf '%s\n' "$a05bd_nonce completed" > "$a05bd_state/last-reset"
    chmod 600 "$a05bd_state/last-reset"
    rm -f -- "$a05bd_state/pending"
    sync
    tell_kmsg 'A05BD factory reset: completed; seeding clean writable paths'
}
