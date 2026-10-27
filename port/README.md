# Ubuntu Touch device port sources

initrd/ はHalium initrdの変更後ソース、gstreamer/ はION plugin、kernel-patches/ はcamera CMDQ互換修正、qt/ はcross build設定です。rootfs-overlay/ は収集した設定のビルド入力です。port-build/prepare-rc1.py とfinish-rc1.pyが最新のFactoryReset V2、root console、所有権、locale/schema等を適用するため、古いoverlayを動作中の端末へ一括適用しないでください。

PCインストーラーは../installer/、通常の導入はReleaseの展開物で行います。このディレクトリーだけでUbuntuの全packageを再構築するものではありません。kernel/Qt完全source、packages.tsv、SOURCES.mdを併用します。個体固有GPT/NVRAM/ユーザーデータは同梱していません。
