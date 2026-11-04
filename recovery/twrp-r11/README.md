# A05BD TWRP R11 / 2026-11-04

Same pinned upstream source/kernel/DTBO as R9. Portrait UI and input calibration.
Create configfs functions/ffs.adb BEFORE mounting FunctionFS. Remove the generic
premature duplicate mount. Restart adbd on boot after endpoints are ready.
Set sys.usb.ffs.aio_compat=true before startup: the vendor 4.14 FunctionFS AIO
path drops data beyond unaligned 24-byte ADB reads. Kernel f_fs.c explicitly
notes this affects AIO, while synchronous reads split the request safely.
The existing ADB synchronous path is selected, with no C++ implementation change.

R9 runtime fixes were confirmed with USB root ADB. R11 dedicated recovery mode2 automatic USB/root ADB, two complete 1.58GB
transfers and a real TWRP clean install with full readback succeeded. See the
release report for exact SHA and scope. R11 build.prop retains the R9 incremental
string; init-file and full partition SHA verify the updated recovery contents.
Build uses retained CT104 cache with CPUQuota100% / Nice10. Browser sources kept.
