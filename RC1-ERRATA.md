# RC1のインストーラーに不足（2026-10-27）

RC1のRAM recoveryには`/usr/bin/dd`と`/usr/bin/openssl`が収録されていません。RC1インストーラーはこれを要求するため、RAM recoveryへのBOOT変更後、backupの前提検査で停止します。**RC1を新規インストールには使用しないでください。** RC2では収録済みBusyBoxの命令だけを使い、同じARM64バイナリーで位置指定の読み書き・SHA照合等を検証して修正しました。

この停止はsystem/data/GPT書込み前です。すでにbootstrapだけ実施した場合は、fastbootから自身の`original-boot.img`を戻す手順をRESTORE.mdに記載しています。RC1の画像内容が壊れていると確認したわけではありません。現時点の作業端末への書込みはしていません。

2026-10-27追記：ユーザーの明示指示でRC1 ZIP・checksum・展開buildを削除した。訂正記録と既存の復元用backup、RC2は保持。RC3では全体backup省略を明示選択する経路を追加して試験中。
