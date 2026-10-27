# Morph / Qt WebEngine R5 source

MorphのUI本体を独自forkしたものではなく、Qt6 WebEngine/ChromiumにMediaTek ION H.264 decoderとMojo経路を追加しています。qtwebengine/は変更した8fileと近接licenseの抜粋、完全な変更後ソースはReleaseの qt6-webengine-6.11.2-a05bd-r5-source.tar.gz です。build-inputs/revision5-manifest.jsonのafter SHAとこの抜粋を全件照合済みです。

ソース由来はQt6 WebEngine6.11.2、外側runtime ABI表記は6.10.2です。正しいhost QtとARM64 targetライブラリを用意し、build-inputs/build/CMakeCache.txtとargs.gn、../port/qt/webengine-cross-toolchain.cmakeを参照します。ビルドディレクトリーは当時の /build/qt6-webengine-cross、環境はNoble amd64 chrootからaarch64へのcross buildです。

実機の通常MorphでH.264 HW decode/同期を確認しています。AV1 HW/zero-copyは対応していません。新しい環境での完全再現ビルドは未検証です。コード・Qt・Chromiumの各licenseを保持し、全体の使用部品は../LICENSES.txtを参照してください。
