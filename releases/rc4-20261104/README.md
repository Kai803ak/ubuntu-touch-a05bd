# TAB-A05-BD / Ubuntu Touch RC4 + TWRP R11 / installer R2

**実TWRPからsystem・BOOT・userdataの新規導入と、全書込イメージの読み戻し検証に成功しました。**
ユーザー指定で内部ユーザーデータを消去。既にUbuntu用6GiB system配置になっている実機で試験しました。
通常Ubuntuへ再起動し、初期設定・タッチ・日本語「次へ」を利用者が確認済みです。電源オフ充電サービス・電池状態・自動消灯の回帰も確認しました。通常Ubuntuへ戻した状態で作業を終えています。詳しくはreport.mdを参照。

## 使うファイル

- `recovery-a05bd-ut-r11-avb.img`：専用recovery用、16MiB。縦向きTWRP 3.7.0_9-0。
- `a05bd-ubuntu-touch-rc4-twrp-clean-install-r2-20261104.zip`：約1.58GB、**データ消去**。
- `a05bd-ubuntu-touch-rc4-twrp-update-r2-20261104.zip`：既存Ubuntu配置のデータ保持更新。実機では未試験。
- [導入手順](INSTALL-TWRP.md)、LICENSES.txt、SHA256SUMS、各source archiveを同梱。
- kernel/Qt全source・元RC3の制限は [元RC3 Release](https://github.com/Kai803ak/ubuntu-touch-a05bd/releases/tag/rc3-20261027) を参照。

## 今回の修正

- 電源オフ充電の残量％、自動消灯、短押し再表示、長押し通常起動をsystem imageに追加。
- TWRPはUSB FunctionFSを作成後にmountし、準備後にADBを起動。自動root ADBを実機確認。
- vendor4.14のUSB AIOでADB headerが欠落するため、既存同期I/O互換モードを使用。
  1.58GB全転送2回完走、実再導入後のkernelデータdrop警告0。
- installerはTWRPの通知FD23へ対応。初版の失敗は書込前停止、修正後に実機無書込probeと全導入を実施。

## 検証範囲

圧縮・展開image SHA、e2fsck、実TWRPのARM64 Python、clean実書込・全readbackを確認。
BOOT/recovery全領域SHAとGPT両copyの保持も確認。新規導入処理は500秒。
LK/preloader/NVRAM等の固有firmwareは保持。backupはBOOT/recoveryの限定控えだけで、userdata全体backupは作成していません。

Android旧配置からのGPT移行、GUIでのZIP選択、microSD、ADB sideload、update ZIPの実機導入は今回未試験。
Android移行とupdateの保持はPCの実ファイルfixtureで検証したもので、実機成功と混同しません。
深いsuspend・完全再現build/全対応source/一部再配布条件の未確認点は元RC3から継続。
GitHubの旧RC3公開物は変更していません。
