#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
# Usage: wrap-r11-avb.sh PYTHON2 AVBTOOL RAW_R11 OUTPUT
set -euo pipefail
python_bin="$1"; avb_tool="$2"; raw_image="$3"; output_image="$4"
test -f "$raw_image"
test ! -e "$output_image"
test "$(sha256sum "$raw_image" | cut -d ' ' -f 1)" = cae9483c779cc994bd100e58637b38bddaf38403bf53559c26fca9bd556c8c69
stage_dir="$(mktemp -d)"
trap 'rm -rf "$stage_dir"' EXIT
cp "$raw_image" "$stage_dir/recovery.img"
"$python_bin" "$avb_tool" add_hash_footer --image "$stage_dir/recovery.img" \
  --partition_size 16777216 --partition_name recovery --algorithm NONE \
  --salt c6c2eab2c241aa0713e6cf5ed63bc0728b9ea860c506ed3b81b555ee20da3351
"$python_bin" "$avb_tool" verify_image --image "$stage_dir/recovery.img"
test "$(sha256sum "$stage_dir/recovery.img" | cut -d ' ' -f 1)" = 047ae969f79adc7bfd290e79da76985f2db3e74b58702b507bcce34e66406928
cp "$stage_dir/recovery.img" "$output_image"
