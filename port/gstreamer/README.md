# MT8168 ION decoder v0.3 / PTS drain correction

Vendor kernel STOP marks LAST on `input_max_ts`. v0.2 passed decode-order frame IDs as timestamps; B-frame reorder could mark LAST before the final reference picture. The 60-frame synthetic AVC reproduced a 59-frame result (frame ID 57 missing). v0.3 passes presentation timestamps and maps returned timestamps back to queued GStreamer frames, rejecting missing/ambiguous PTS.

Validated as phablet on kernel #6: reset before EOS, then all 60 ordered NV12 hashes; seek simulation from IDR AU30, all 30 ordered hashes; 1080p MP4, all 30 ordered hashes. Max PTS difference vs reference: 333ns. This does not execute the new Chromium class.

Requires valid input PTS. A raw H.264 filesrc test without timestamps failed (0 frames); MP4/qtdemux works. The old installed v0.2 plugin remains unchanged for earlier callers. Do not load both versions in one process.

New opt-in installation: `/usr/local/lib/a05bd-gst-pts/libgsta05bdiondec.so`, rank NONE, root:root 0644. SHA256: `12ead525c59d4edc2e6cf9170bfcd0952c7fe2d09f17fc5f21d6d04c9694d5da`. Cached output requires `A05BD_ION_CAPTURE_CACHED=1`; otherwise the existing uncached path is used.

Build for ARM64 with GStreamer video development headers and the included ION headers:

```sh
${CC:-cc} -O2 -Wall -Iinclude -shared -fPIC -o libgsta05bdiondec.so gsta05bdiondec.c $(pkg-config --cflags --libs gstreamer-video-1.0)
```

For cross compilation, select an ARM64 compiler and ARM64 pkg-config directories. No local VM is required. Preserve the license notices in the source and headers.

Device backup/rollback: `/var/backups/a05bd-port/webengine-ion-20261022-pts/`. Root `python3 .../rollback.py` removes only this new plugin if hashes still match; it does not replace the old plugin. Host backup: `../pts-plugin-backup.tgz` (49395 bytes), SHA256 `4eebae689b749e8a251986ff1528d324b245e9bab392e9257ab4126f10691ffe`.
