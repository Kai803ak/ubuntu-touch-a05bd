# ソースと再ビルド資料

このRCの`manifest.json`がバイナリーとソースアーカイブのハッシュを対応付けます。ライセンス・使用部品・未確認事項の一覧は**LICENSES.txt**に集約しています。`packages.tsv`はUbuntu/UBportsパッケージのbinary/source版の台帳です。

- `sources/kernel-4.14.87-a05bd-6-source.tar.gz`：実際の#6ビルドに使用したカーネル作業ツリー、最終config、元build script、コンパイラー情報。生成した秘密署名鍵とオブジェクトは除外しています。Image.gzと、別途追加されたDTB/DTBOの由来・生成条件は区別します。
- `sources/qt6-webengine-6.11.2-a05bd-r5-source.tar.gz`：実際の変更後Qt WebEngineソースツリー。Chromium内IONデコーダーとMojo配線を含みます。外側のABI名は6.10.2ですが、ソースの由来は6.11.2です。
- `sources/qt-build-inputs-rc1.tgz`：実際のCMakeCache/GN設定、存在する場合はR5変更マニフェスト。ビルド環境のパスは当時のものなので、新環境では読み替えます。
- `sources/port-sources-rc1.tgz`：独自設定、変更スクリプト、GStreamer ION plugin、キーボード、スピナー用ソース、カーネル追加パッチなど。各ファイルの元の著作権表示を保持します。
- `installer/`：今回のPCインストーラーとGPT計画処理そのもののソースです。

カーネルはLinux amd64環境のaarch64-linux-gnu-gcc-9でビルドしました。アーカイブ内の`kernel-build-inputs/kernel.config`を出力先`.config`へ置き、元build scriptの`/opt/...`を展開先へ読み替えてください。MT8168のカメラ互換修正は変更後ツリーに含まれます。

Qt WebEngineはUbuntu24.04 amd64上でARM64へcross buildしました。ARM64 Qt開発環境、対応するhost Qt tools、Chromium依存ツールと十分なディスク/RAMが必要です。保存したCMakeCache/GN設定とtoolchain資料を参照してください。ソースの再ビルド・差し替えでバージョン名だけを変更せず、ランタイム側QtとのABI整合も確認します。新環境での完全な再現ビルド試験は未完了です。

GStreamer pluginのビルド例は同梱ソースREADMEにあります。日本語QML/JSと端末設定はイメージ内でも読み出せる形式です。

未変更のディストリビューションパッケージの対応ソースは、台帳のsource package/versionに一致するものをUbuntu/UBportsの対応source repositoryから取得します。`apt source --download-only 名前=ソース版`を使用できますが、適切なdeb-src設定と、その版の提供有無の確認が必要です。全パッケージのソースをこのZIPに同梱したという意味ではありません。

**残る確認**：全体の対応ソース充足性、再現手順、DTB/DTBO、Android HAL/GPU/firmwareの再配布許諾。これらを「LICENSES.txtを書いたので確認済み」とは扱っていません。

RC3の転送修正はinstaller/install.pyにあります。32MiB転送とメモリguard、macOSの一時sleep抑止を含みます。sources/test-chunked-transfer.py、rc3-reset-test.py、rc3-live-health.pyとvalidation/にfixtureおよび実機試験の資料を追加しています。これらの試験は既存の初期調査/ビルド環境を参照するものを含み、全モードの自動再現試験を意味しません。
