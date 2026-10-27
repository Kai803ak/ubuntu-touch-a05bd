# TAB-A05-BD Ubuntu Touch RC3 インストール

このRCは開発者向けです。再生成イメージの実機書込み・system起動・表示/タッチ・日本語初期設定・初期化を確認済みです。検証には転送不具合の修正と状態を明示確認した再開を含みます。無停止の全工程と全モードを検証済みという意味ではありません。rootコンソールは利用者の要望により有効です。USBを接続したPCから認証なしでrootシェルへ入れます。

対象はアンロック済みチャレンジパッドNeo TAB-A05-BD/a05bd、16GB eMMC（30535680セクター）、Android9系の対応ベースです。他機種・容量違い・異なるベースファームウェアは対象外です。インストーラーは対象外なら停止します。アンロックやDRM解除の機能は含みません。

必要なものはmacOS/Linux、Python 3.11以降、PATH上のadb/fastboot、USBケーブルです。PCに少なくとも30GB程度の空きを用意してください。作業中は電源を確保します。macOSではCLI実行中だけcaffeinateで自動スリープを抑え、終了時に解除します。Linuxでも作業中はPCがスリープしない状態にします。

## 1. 配布物を検査する

配布ZIPを展開したフォルダーで実行します。フォルダー内のファイルを個別に入れ替えないでください。

```sh
python3 installer/install.py verify
```

SHA256SUMSと配布者が別途示すチェックサムも照合してください。チェックサムは破損検知用で、配布者の署名ではありません。

## 2. 元のBOOTを退避してBootloaderへ入る

元のAndroidでroot ADBが使える場合の例です。**この端末自身のBOOT全16MiB**をPCへ保存します。他人のBOOTバックアップを代用しません。

```sh
mkdir -m 700 ../a05bd-private-backup
adb exec-out su -c 'dd if=/dev/block/mmcblk0p14 bs=1048576 count=16' > ../a05bd-private-backup/original-boot.img
adb reboot bootloader
```

suのメッセージが混入していないこと、16777216バイトであることを確認します。元BOOTを取得できない場合は先へ進みません。現在Ubuntu環境から更新する場合は、その環境のroot権限で同じBOOT全体を退避し、BOOTとsystemを含む現在の復元経路を確保してください。

ADBでBootloaderへ入れない場合は、PCで次を開始してから、USB接続のまま端末を再起動します。MediaTek preloaderのREADYに対してFASTBOOTを送る接続補助で、パーティションへは書き込みません。

```sh
python3 installer/enter-fastboot.py
fastboot devices
```

## 3. インストール用RAM recoveryへ切り替える

```sh
python3 installer/install.py bootstrap --original-boot ../a05bd-private-backup/original-boot.img --backup-dir ../a05bd-private-backup --execute
adb devices
```

**ここでBOOTだけを一時的に書き換えます。** system/data/GPTはまだ変更しません。RAM recoveryは操作画面を表示しないため、最初のロゴのままでもADBが認識されれば正常です。`backup`がRAM recoveryの識別マーカーを検査します。ADBが認識されない場合は追加の書き込みをせずRESTORE.mdの「BOOTだけ戻す」を実行してください。

横向きTWRP R7/R8はこの配布物のインストールには使用しません。

## 4. 全eMMCをバックアップする

```sh
python3 installer/install.py backup --backup-dir ../a05bd-private-backup
python3 installer/install.py plan --backup-dir ../a05bd-private-backup
```

全eMMC約15.6GBをPCへ読み出し、端末上のSHA256と比較します。通常のAndroidやUbuntuが動作中の状態では実行できません。全バックアップ内のBOOTは一時RAM recoveryなので、元BOOTは別ファイルとして必ず保管します。

バックアップには個人データ・校正・認証情報が含まれ得ます。配布ZIPと混ぜず、公開しないでください。

primary/secondary GPTが、それぞれCRC正常でも互いに異なる場合は既定で計画を拒否します。バックアップを保管し、primary側が意図した構成であることを確認した場合だけ、次の明示指定で計画を確認します。p1〜p27が一致しない状態はこの指定でも拒否します。

```sh
python3 installer/install.py plan --backup-dir ../a05bd-private-backup --use-primary-gpt
```

## 5. インストールする

**初回導入：Androidと既存の利用者データを消去します。** systemを6GiBへ拡張し、その端末のvendor/factory/cacheをバックアップから移動します。端末固有GPT GUIDとp1〜p27は保全し、最後にBOOTをUbuntuへ変更します。LK/preloader/NVRAM/recovery/top-level vbmetaは書き換えません。

```sh
python3 installer/install.py install --backup-dir ../a05bd-private-backup --erase-userdata --execute
```

前段でprimary GPTを明示選択した場合に限り、上にも`--use-primary-gpt`を追加してください。

**既存の同じUbuntuパーティション構成から更新：** userdataのUTdataラベルと配置が一致する場合に限り、データを保全するモードも使えます。

```sh
python3 installer/install.py install --backup-dir ../a05bd-private-backup --preserve-userdata --execute
```

転送は32MiBずつ書込み・同期の完了を待ち、端末の空きRAMとadbdの使用量も検査します。各イメージは読み戻したSHA256を照合します。途中で停止したら無条件に再実行せず、ログとバックアップを保管してRESTORE.mdへ進んでください。インストーラーは中断した導入の自動再試行を拒否します。

完了後は再起動し、初回設定を進めます。日本語入力は標準キーボードに組み込んであります。既知の制限はKNOWN-ISSUES.md、使用データ・ライセンス・ソースの状況はLICENSES.txtを参照してください。

## 全体バックアップを省略する場合

通常は上の全eMMCバックアップを使用します。空き容量の事情などで明示的に省略する場合だけ、手順4の代わりに次を実行します。手順2・3の端末自身の元BOOTは必要です。新しいセッションディレクトリーを使います。

```sh
python3 installer/install.py prepare-no-backup --backup-dir ../a05bd-private-backup --accept-data-loss
python3 installer/install.py plan --backup-dir ../a05bd-private-backup
python3 installer/install.py install --backup-dir ../a05bd-private-backup --without-full-backup --accept-data-loss --erase-userdata --execute
```

この経路は全eMMCやユーザーデータのバックアップを作りません。PCに保存するのは元BOOT、GPT、CID・検査ハッシュ・作業記録です。vendor/factory/cacheを端末内の重ならない範囲へ直接コピーし、各範囲を読み戻して照合してからGPTを変更します。移動先となる旧userdata領域は消去対象です。元のユーザーデータの復元はできず、このセッションに`restore`を実行しても復元できません。事前に別途確保した対応ROMや既存の完全バックアップが必要です。

primary/secondary GPTの明示選択が必要な端末では、上の3コマンドすべてに`--use-primary-gpt`を加えます。途中で停止したらそのセッションを無条件に再試行しません。通常のバックアップ必須モードの検査は維持しています。

## USB rootコンソール

通常Ubuntu起動中は、macOSでは`/dev/cu.usbmodema05bd_ut1`、Linuxでは該当する`/dev/ttyACM*`を115200bpsで開きます。例：

```sh
screen /dev/cu.usbmodema05bd_ut1 115200
```

同じポートを複数のプログラムで同時に開かないでください。rootシェルなので、このコンソールで実行するコマンドはそのままシステム全体へ作用します。
