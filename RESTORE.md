# 復元手順

復元には、対象端末自身の`a05bd-private-backup`を使います。他人の全eMMC/GPT/NVRAMを使用しません。インストール失敗後も、バックアップと`backup.json`、元の`original-boot.img`を保存してください。

## BOOTだけを戻す

RAM recoveryの起動に失敗し、system/data/GPTをまだ変更していない場合に使います。`installer/enter-fastboot.py`を先に開始して、USB接続のまま電源ボタンを10〜15秒長押しし、再起動したら離します。fastbootの認識後に実行します。

```sh
fastboot devices
fastboot flash boot ../a05bd-private-backup/original-boot.img
fastboot reboot
```

BOOTだけでは、変更済みのsystem/GPT/userdataは元に戻りません。

## 全ディスクを元に戻す

`prepare-no-backup`で作ったセッションには全ディスクの復元機能はありません。元BOOTだけでは消去したsystem/userdataや変更済みGPTを元に戻せません。以下は`backup`で取得・照合した完全バックアップがある場合の手順です。

まず一時RAM recoveryへ戻します。fastbootが認識されている状態で実行します。

```sh
fastboot flash boot recovery-ram.img
fastboot reboot
adb devices
python3 installer/install.py restore --backup-dir ../a05bd-private-backup --execute
```

復元はeMMC CID、バックアップのサイズ・SHA256、元BOOTを検査します。全ディスクを読み戻してSHA256を照合した後、別途保存した元BOOTをp14へ戻し、再起動します。インストール前の状態へ戻るため、インストール後に作成したデータは失われます。

RAM recoveryへも入れない場合は作業を止め、バックアップを保全してください。BROM/preloaderの書き換えや他端末のGPTを使う復旧は、この配布物の対象外です。
