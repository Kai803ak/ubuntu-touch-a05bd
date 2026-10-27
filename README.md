# チャレンジパッドNeo / Ubuntu Touch RC3

## RC3をインストールする

[RC3 Release](https://github.com/Kai803ak/ubuntu-touch-a05bd/releases/tag/rc3-20261027)から次の5ファイルを同じフォルダーへダウンロードします。ソースリポジトリをcloneしただけではOSイメージは入りません。

- `a05bd-ubuntu-touch-24.04-20261027-rc3.zip.part01`
- `a05bd-ubuntu-touch-24.04-20261027-rc3.zip.part02`
- `a05bd-ubuntu-touch-24.04-20261027-rc3.zip.part03`
- `rc3-download.json`
- `assemble-rc3.py`

```sh
python3 assemble-rc3.py
unzip a05bd-ubuntu-touch-24.04-20261027-rc3.zip
```

結合スクリプトは各partと元ZIPのSHA256を検査します。結合済みZIPは今回実機で使用したものと同じ2904897818バイト、SHA256 `808854c2fc2ee3f412bd66bd8a444e7774e5b69c817da148da7151151b67856a`です。GitHub Releaseの1ファイル2GiB制限のため分割しています。ZIPと全partを併せて約6GB、全backupを取る場合は導入手順の追加容量を確保してください。

**導入コマンドは結合・展開したRC3のフォルダー内で実行します。** [INSTALL.md](INSTALL.md)・[RESTORE.md](RESTORE.md)を参照してください。

## ソース

`browser/`にChromium/Qtの変更箇所とビルド設定、`kernel/`に実際のkernel設定、`port/`にUbuntu Touchのinitrd・rootfs設定・GStreamer・日本語キーボード等、`installer/`にPCインストーラーを置いています。変更済みQt WebEngineとkernelの完全ソースarchiveはReleaseにも個別添付します。Ubuntu Touch/Ubuntu/UBports全体の全packageソースを一つのGitに収録したものではありません。[SOURCES.md](SOURCES.md)と`packages.tsv`の版・上流URLを確認してください。


TAB-A05-BD向けUbuntu Touch 24.04系の非公式・開発者向けインストール候補です。再生成したイメージを実機へ書き込み、**systemからの起動、表示・タッチ、日本語の初期設定、Wi-Fiスキャン、初期化と再起動**を確認しました。

含まれる構成はkernel4.14.87 #6、Lomiri、MorphのH.264 HWデコード、日本語QWERTY、2GiB zram、カメラ/回転/電源キー修正です。通常モードでは全eMMCバックアップを使用します。空き容量の事情などで省略する場合は、元BOOTと小さな検査記録を保持する明示モードを選べます。

- [INSTALL.md](INSTALL.md)：初回導入・既存の同一Ubuntu構成からの更新
- [RESTORE.md](RESTORE.md)：BOOT復元・全eMMCバックアップからの復元
- [KNOWN-ISSUES.md](KNOWN-ISSUES.md)：制限と未検証の範囲
- **LICENSES.txt**：使用部品・著作権表示・ライセンス本文・由来・未確認事項を集約した単一テキスト
- [SOURCES.md](SOURCES.md)、`sources/`、`packages.tsv`：ソースとビルド資料
- `manifest.json`、`SHA256SUMS`：同梱ファイルとイメージの照合情報
- `validation/`：実機とfixtureの検証結果

systemを6GiBへ変更し、端末自身のvendor/factory/cacheを移動します。各書込みを読み戻してSHA256を照合し、端末固有GPT GUIDと保護firmwareを保持します。他人のGPT/NVRAMを配布・適用しません。通常の全バックアップモードと、既存の同一Ubuntu構成でuserdataを保全するモードもあります。バックアップ省略モードには、元ユーザーデータや全ディスクの復元機能はありません。

RC2の連続ADB転送でadbdがメモリ不足に陥る問題を修正し、RC3は32MiBごとの書込み完了待ちとメモリ検査を使用します。macOSではCLI実行中だけ自動スリープを抑えます。RC1/RC2を新規導入に使用しないでください。今回の実機検証はAndroid初期起動→GPT移行→転送中断の原因調査→修正版で明示的に状態を再検査して残工程→Ubuntu起動/初期化という経路です。修正後installerの旧Android配置から全工程を無停止で一度に通す試験と、新installerの全backup/restore/preserveモード全体は未実施です。

**USB rootコンソールは利用者の要望により有効**です。USB接続PCから認証なしでrootシェルへ入れます。TWRPは使用せず、一時BOOTのRAM recoveryで導入します。最初のロゴは端末の既存logo領域を使用し、その後のUbuntu読み込み表示は横向きです。

ライセンスの表記と、全部品の再配布権・対応ソースの確認完了は別です。Android HAL/GPU/firmwareなどの未確認事項をLICENSES.txtに記録しています。このRCを権利確認済みの一般向け完成版とは表示していません。
