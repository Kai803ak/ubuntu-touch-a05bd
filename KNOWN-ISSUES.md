# 既知の制限（2026-11-05、RC4開発版）

- 深いサスペンドからの復帰は未解決。画面消灯・ロックは動くが、mocksuspend/autosleep offで回避しており待機消費電力が増える。
- MorphのH.264 HWデコードと音声同期は確認済み。YouTubeはH.264を優先する。720p60は多くのframe dropがあり、480pを実用の目安とする。AV1 HW/zero-copyは未対応。
- Bluetoothはcontroller/BLE探索まで。音声機器のpairing/再接続の十分な検証は未完。
- 公式OTAへの追随や無条件のOS更新は保証していない。固有kernel/HAL/Qt WebEngineの変更がある。
- 電源の短押し消灯・復帰は2026-10-26に修正し、長押しメニュー/通常再起動後の動作も利用者確認済み。
- RC4は既にUbuntu配置の実機へTWRPからsystem/data/BOOTを全新規導入し、全readback・通常起動・初期設定/タッチ/日本語次へ・充電回帰を確認。旧Android配置からの移行、update ZIP、GUIのZIP選択/microSD/ADB sideloadは今回実機未試験。
- RC3の実機書込み・起動・表示/タッチ・日本語初期設定・FactoryReset V2は確認済み。試験は初回の連続転送OOMを診断し、修正後にGPT/移動済領域/保護firmwareを検査して残工程を完了したもの。修正後installerで旧Android配置から無停止で全工程を通す試験と、新installerの全backup/restore/preserveモード全体は未実施。
- TWRP R11は縦向き、専用recovery mode2で自動root ADBとinstaller R2によるclean導入を確認。横向き版は未提供。初版TWRP ZIPはFD23問題があるため使わず、R2を使用する。
- TWRPの通常wipeをUbuntuの初期化に使わない。Ubuntuの設定APIからのfactory resetは実機で一度検証済みだが、RC3は機体UUID固定をやめ、runtimeのUUIDと対応するpartition境界を検査します。V2の実初期化でcanary消失・完了stamp・UUID/主要設定保持・新boot ID・初期設定画面への復帰を確認しました。
- stock layoutのsystem容量では入らない。初回のパーティション構成変更は、既存移植環境のsystem更新とは異なる作業になる。

USB root診断口は利用者指定で有効です。個人情報の既知パスを除外し、インストール/復元手順とソース資料を同梱します。再配布権・全体の対応ソース充足性・再現ビルドの最終確認は残ります。

- RC1/RC2は新規導入に使用しない。RC2のadbd OOMはRC3で分割転送とメモリ検査へ修正。詳細はRC2-ERRATA.md。

- `fastboot reboot recovery`はOKAYでも今回の経路では通常Ubuntuへ戻った。現行INSTALL-TWRP.mdに記載したnormal rootのsystemd reboot-param recoveryでmode2を確認している。
- R11のbuild.propはR9 incremental文字列を保持する。配布image SHAと修正initファイルSHAでR11を識別した。
