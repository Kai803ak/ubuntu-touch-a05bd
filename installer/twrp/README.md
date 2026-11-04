# TWRP installer R2

`flash.py` / `layout.py`は実機のclean導入とPCの9ケースfixtureで検証したソースです。`update-binary`はTWRPの通知pipe FD23を `/proc/self/fd/$outfd` で扱います。古いmkshの `>&23` 制限を実機probeで確認してから修正しました。

Release ZIPは添付のARM64 Python runtimeをRAMへ展開して実行します。runtime packageの版・hashはこのフォルダー、対応sourceはRC4 Releaseの `python-runtime-corresponding-sources.tar.gz` にあります。各package copyrightも単一LICENSES.txtへ収録しています。

インストーラーは未マウントの内部eMMC、機種・容量・GPT・vbmeta、battery / RAM、全payloadの圧縮・展開SHAを検査してから書き込みます。cleanはuserdataを消去、updateは既存6GiB system / UTdata配置だけを受け付けます。4MiB streaming / 32MiB fsync、全system / data読み戻し、保護firmware検査、BOOTを最後に更新する処理です。失敗時の自動再試行・rebootは行いません。

実機ではTWRP CLIのexit0だけでなく、RAMsessionの `ALL_WRITTEN_IMAGES_READBACK_VERIFIED` を確認しました。[現行手順](../../INSTALL-TWRP.md)・[試験結果](../../releases/rc4-20261104/report.md)を参照してください。updateと旧Android配置からの移行は今回実機未試験です。

`test-flash.py`は当時の作業ディレクトリを使うfixtureの記録で、公開checkoutだけで全buildを自動再現するものではありません。block deviceに対して試験を実行しないでください。
