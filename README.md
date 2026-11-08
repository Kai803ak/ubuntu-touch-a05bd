# チャレンジパッドNeo / Ubuntu Touch RC4

## Codex制作です！！！実験程度に使ってください。
Nextに移行するのでアーカイブします。

TAB-A05-BD（MT8168、16GB）向けの非公式・開発版です。**RC4・TWRP R11・installer R2を実機で新規導入し、system / userdata / BOOTの読み戻し検証、通常起動、初期設定・タッチ・日本語「次へ」を確認しました。** 電源オフ充電の残量％・自動消灯もイメージへ反映しています。

## ダウンロード・導入

[RC4 Release](https://github.com/Kai803ak/ubuntu-touch-a05bd/releases/tag/rc4-20261104)から取得してください。OSイメージはGitのcloneやGitHub自動生成の「Source code」ZIPには含まれません。

| ファイル | 用途 |
|---|---|
| `recovery-a05bd-ut-r11-avb.img` | 専用recoveryへ入れる縦向きTWRP、16MiB |
| `a05bd-ubuntu-touch-rc4-twrp-clean-install-r2-20261104.zip` | 新規導入、約1.58GB。**内部ユーザーデータを消去** |
| `a05bd-ubuntu-touch-rc4-twrp-update-r2-20261104.zip` | 既存の6GiB system / UTdata配置を保持して更新。実機未試験 |
| `SHA256SUMS` | ダウンロードした添付ファイルの照合 |

ZIPは展開せずTWRPのInstallへ渡します。[INSTALL-TWRP.md](INSTALL-TWRP.md)と[実機検証報告](releases/rc4-20261104/report.md)を先に読んでください。今回の実機は既にUbuntu用のパーティション配置であり、**旧Android配置からのGPT移行をこのTWRP版で実機検証したものではありません。** GUIでのZIP選択、microSD、ADB sideloadも今回の試験対象外です。

実機ではTWRPのRAMへ32MiBずつ転送し、全ZIPのSHA256を検査した後、実際のTWRP Install処理で全新規導入しました。処理は約8分20秒。system / userdataの全領域読み戻しとBOOT、保護firmware、GPTを検証しています。固有のLK / preloader / NVRAMを配布イメージで上書きしません。

## RC4で追加した修正

- 電源オフ充電の残量％表示、自動消灯、短押し再表示、長押し通常起動。新規導入後の充電サービス・電池状態・消灯・通常復帰も確認。
- TWRPのFunctionFS初期化順序を修正し、専用recoveryでUSB root ADBの自動接続を確認。
- vendorカーネルのUSB AIOで起きるデータ欠落を、ADBの既存同期I/O互換モードで回避。
- installerの通知FD23への出力を修正。**初版のTWRP用ZIPではなく、ファイル名に`r2`のある版を使います。**

kernel 4.14.87 #6、Lomiri、MorphのH.264 HWデコード、日本語QWERTY、2GiB zram、カメラ・回転・電源キーの修正はRC3から継承しています。深いsuspendなどの[既知の制限](KNOWN-ISSUES.md)は残ります。

## ソース・検証結果

- [browser/](browser/)：変更したQt / Chromiumのソースとビルド設定。
- [kernel/](kernel/)：kernel設定・変更入力。完全なkernel / Qt source archiveは[RC3 Release](https://github.com/Kai803ak/ubuntu-touch-a05bd/releases/tag/rc3-20261027)に保持。
- [port/charging/](port/charging/)・[rootfs-overlay](port/rootfs-overlay/)：充電のsource / patch / systemd設定。
- [recovery/twrp-r11/](recovery/twrp-r11/)：TWRPの固定revision・device tree・init修正・AVB wrapper資料。
- [installer/twrp/](installer/twrp/)：TWRP内で動くinstaller R2のソース。
- [releases/rc4-20261104/](releases/rc4-20261104/)：配布ファイルのSHA・実機検証結果・手順。
- [SOURCES.md](SOURCES.md)、`packages.tsv`、単一の[LICENSES.txt](LICENSES.txt)：部品・対応source・ライセンス一覧。

USB rootコンソールは利用者指定で有効です。USB接続PCから認証なしでrootシェルへ入れる開発用構成です。公式OTAや無条件のOS更新は保証していません。全体の対応source充足性・再現build・一部HAL / GPU / firmwareの再配布条件は確認途中であり、権利確認済みの一般向け完成版とは表示していません。

RC3のPC導入形式は引き続き[旧Release](https://github.com/Kai803ak/ubuntu-touch-a05bd/releases/tag/rc3-20261027)と[旧README](docs/RC3-README.md)に残しています。[INSTALL.md](INSTALL.md)・[RESTORE.md](RESTORE.md)はその方式の資料です。
