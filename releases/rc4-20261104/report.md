# 2026-11-04 TAB-A05-BD 実機導入結果

**実際のTWRP Install処理からRC4を新規導入し、通常Ubuntuの初期設定・タッチ・日本語「次へ」まで確認できた。**
ユーザーの全再導入依頼に従い、system・userdata・BOOTを書き直した。
試験機は事前にUbuntu用6GiB system配置へ移行済みであり、Android旧配置からの移行試験ではない。

| 項目 | 結果 |
|---|---|
| 専用recoveryの起動 | bootmode2、R11のinitファイルSHA・recovery全領域SHA一致 |
| USB root ADB | 手入力なしで自動接続、同期I/O互換モードtrue |
| ZIP転送 | 32MiBごとのSHA＋全ZIP SHA一致、修正版は93.3秒 |
| 実行経路 | `twrp install /tmp/a05bd-rc4-clean-r2.zip`、実update-binary/ARM64 Python |
| system 6GiB | 書込後、全領域SHA一致 |
| userdata 7831272960B | 空userdataを全書込後、全領域SHA一致。旧データ消去 |
| BOOT | 最後に更新、prefixと全16MiBのSHA一致 |
| recovery・固有firmware | installerの保護領域検証成功。recovery全16MiBも別途SHA一致 |
| GPT | primary/secondaryの両copyが実行前と一致 |
| 所要時間 | Install処理500秒（転送時間を含まない） |
| USBデータ欠落 | 修正後のrecovery起動から導入後までkernel警告0 |
| 通常起動 | root `/dev/mmcblk0p28`、mode0、LightDM/repowerd/NetworkManager/Android HAL active、failed0 |
| 初期設定 | 利用者が表示・タッチ・日本語「次へ」の成功を確認 |
| メモリ | 2GiB zram保持 |
| Wi-Fi | 初期化success、wlan0/1が出現。新規データでAP未設定、実接続は未試験 |
| 充電 | 新規導入後mode8、99% Charging/Good、charger/watchdog active、輝度0、failed0。charging-regression.json参照 |

成功判定はTWRP CLIのexit0ではなく、installerの
`ALL_WRITTEN_IMAGES_READBACK_VERIFIED` / `clean=true` を必須とした。
このstateに到達する前に、全payloadの圧縮・展開SHA、各書込image全readback、
保護firmwareとBOOTの検証が走る。RAMsessionとrecovery.logもPCへ取得した。
rootfsは通常起動後に設定等を書き込むため、上の全image SHAは起動前の読戻し結果。

## 修正した問題

1. **FunctionFSの初期化順序**：USB機能ffs.adbの生成より先にmountしていた。
   kernel f_fs.cは未生成instanceにENOENTを返す。生成→mount→ADB起動へ変更。
2. **vendor4.14のUSB AIO**：24BのADB header読み取りで512B受信分の余剰が破棄された。
   kernelの同期read分割経路とADBの既存aio_compat設定を使い、全転送完走・警告0を確認。
3. **高い通知FD**：実TWRPはpipe FD23を渡し、mkshの `>&23` が失敗した。
   初回はPython起動・書込み前に停止。`/proc/self/fd/23`へ直し、無書込probeで
   FD23/root/実ARM64 Pythonを検証した後、修正版ZIPを全検査して実再導入した。
4. **recoveryへの入り方**：fastboot reboot recoveryはOKAYでも通常Ubuntu mode0になった。
   通常Ubuntuからsystemdのreboot-param recoveryを使う経路でmode2を確認した。
   当初のロゴ表示だけをrecovery/kernel起動失敗とする判断は取り消す。

PCがスリープへ入りかけたとの申告もあったが、kernelのAIO欠落ログがあるため、
転送停止をPCだけの原因とはしていない。作業中だけMacの自動スリープを抑止した。

## 同梱イメージ

- clean R2 ZIP SHA256: `54209f5565d4c5e7992e01ecf6021eaffe499ba0aeee13fde67724997e272bd7`
- system raw SHA256: `ec6bd18fdbc15bcdaa4ecbf171bab25e1d29851e685cfefefdeeeae011eb815e`
- recovery R11 AVB SHA256: `047ae969f79adc7bfd290e79da76985f2db3e74b58702b507bcce34e66406928`
- update-binary SHA256: `6e4aba52a3722bd4762042109b79c674a268f4b05cd8275384adf44ff88f9817`

充電修正は公開RC3の検証済みbase imageへ追加した。稼働端末のrootfsや個人データを
丸ごと取り込んでいない。追加全fileのSHA/mode/owner、e2fsck exit0、AVB tail保持を検査。
R11は同じkernel#6/DTBOを使用。build.propのincremental文字列にはR9が残るが、
initファイルSHAと全recovery image SHAでR11の内容を実機照合した。

## 範囲と残課題

今回実機で導入したのはclean ZIP。update ZIP、旧Android配置からのGPT移行、
GUIでのファイル選択、microSD、ADB sideloadは実機未試験。
移行・update保持のPC fixture結果は、これらの実機成功を意味しない。
既知の深いsuspend問題、完全再現build/全対応source・一部再配布条件の未確認点は元RC3から継続。
初版RC3用TWRP ZIP・初版RC4 ZIPにはFD23問題があるため使わず、R2を使う。
GitHubの旧RC3 Releaseは変更していない。

充電画面の％・短押し再表示・長押し通常起動はイメージ化前に利用者確認済み。
新規導入後は充電target/電池状態/消灯をPC側で再確認した。

最終状態は通常Ubuntu mode0、主要4service active、failed0、輝度102、2GiB zram。
初期設定の状態で残した。final-normal-state.json参照。
