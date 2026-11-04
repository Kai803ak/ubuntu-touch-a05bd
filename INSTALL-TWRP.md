# TAB-A05-BD / Ubuntu Touch RC4 + TWRP R11 / installer R2

対象はアンロック済みMT8168 / 16GB TAB-A05-BD。端末の固有firmwareは保持します。
実機検証結果はREADME.md/report.mdを先に読み、SHA256SUMSを照合してください。
ZIP内のINSTALL-TWRP.mdは初版作成時の説明で、R9/未検証の記載があります。
現在の対応recoveryはこのフォルダーの `recovery-a05bd-ut-r11-avb.img` です。
初版のinstallerは通知FD>9で停止するため、必ずファイル名に `r2` のあるZIPを使います。

## recoveryの起動

1. BOOT/recoveryの復旧用控えとbootloaderへの経路を確保し、fastbootで
   `fastboot flash recovery recovery-a05bd-ut-r11-avb.img`。
2. 本端末でfastboot reboot recoveryはOKAYでも通常起動になりました。
   正常Ubuntuへ戻し、rootコンソールで次を実行する経路を実機で確認しました。

   ```sh
   printf '%s\n' recovery >/run/systemd/reboot-param
   sync
   systemctl reboot
   ```

   Androidからは `adb reboot recovery` が候補ですが、今回の試験経路とは異なります。
3. 実機でbootmode2、TWRP 3.7.0_9-0、USB root ADB自動接続を確認。
   R11はFunctionFS生成→mount→ADB起動、同期USB I/Oを使います。
   build.propのincremental文字列にはR9が残ります。R11は添付image SHAで識別します。

## Install

- `clean-install-r2`：system/BOOT/userdataを新規導入。**内部ユーザーデータを消去**。
- `update-r2`：既存6GiB system / UTdata専用。ユーザーデータ保持。Androidでは停止。
- 電池30%以上。外部microSD、またはTWRPのRAMへ転送したZIPを使います。
  内部eMMC上のZIPは使えません。system/ubuntu-data等の内部partをすべてunmount。
- GUI Install、または実TWRP CLI `twrp install /tmp/対象ZIP.zip` を実行。
  この試験ではPCから32MiBずつRAM転送し、各chunk/全ZIP SHAを照合しました。
  再起動でRAM上のZIPは消えます。約1.58GB＋runtime約57MBが必要。
- ZIPはPythonをRAMで実行し、全payload圧縮/展開SHAを検証してから書込みます。
  system/data全readback SHA、保護firmware、BOOTを検証し、勝手にrebootしません。
- 成功はTWRP CLIのexit0だけで判断しません。画面/ログのVerifiedと
  `/tmp/a05bd-install-session/state.json` の ALL_WRITTEN_IMAGES_READBACK_VERIFIED を確認。
- エラー時は再実行・再起動せず /tmp/recovery.log とsessionをPC/外部SDへ保管して調査。
  RAMsessionは全体backupではなく、電源断で消えます。

既存AndroidからのGPT移行はPC fixtureでは検証しましたが、今回の実機は既にUbuntu配置です。
kernel/Qt対応sourceと元RC3の制限:
https://github.com/Kai803ak/ubuntu-touch-a05bd/releases/tag/rc3-20261027
