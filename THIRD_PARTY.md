# Third-party provenance and modifications

This is a GPL-2.0-only Linux driver backport, not a clean-room reimplementation.
Original authors, SPDX identifiers and copyright notices remain in the copied files.

## Pinned upstream

- Repository: https://github.com/torvalds/linux
- Commit: `5b0764a53235d3c77e1ed674e836e1b3fe1a4b1f`
- Commit date: `2026-10-24T04:29:02Z`
- Original driver: `drivers/net/can/rockchip/rockchip_canfd-*`
- Driver notices name Pengutronix / Marc Kleine-Budde and refer to the Rockchip CANFD implementation.
- Per-file origin URLs and SHA256 values: `PROVENANCE.json`.

`reference/upstream-driver/` holds the exact original driver files (its Makefile is the upstream directory Makefile).
`reference/compatibility/` holds the original kernel files used for API adaptation and copied helper attribution.
The `GPL-2.0` SPDX identifier in the original kernel sources has its historical GPL version-2 meaning; this project uses GPL-2.0-only.

## Backport changes

`driver/` is the buildable source. Compared with the pinned driver, adaptations cover Linux6.1 CAN data timing member names,
queue helper compatibility, RX echo API naming, cyclecounter callback type, net_device operations and platform remove return type.
The module is named `lbm5_canfd`; legacy compatible matching is guarded for RK3588, and probe requests an exact300MHz CAN clock.

`driver/lbm5_compat.h` contains compatibility helpers derived from the pinned `include/net/netdev_queues.h` and CAN device state helpers.
Their original reference files, including original notices, are included; prefixed names isolate these helpers from other modules.
The original upstream RK3588 FIFO/TDC/errata implementation is retained.

`patches/linux-6.1-backport.patch` records differences for the existing driver files; added compatibility header and Kbuild Makefile
are provided directly under `driver/` and are needed alongside the patch.

New engineering material (root Makefile, public documentation, provenance checks, board overlay and test utility) is distributed under GPL-2.0-only.
The source release contains no precompiled module; the recorded module hash identifies the binary that was actually field-tested.
No claim of upstream acceptance, official vendor support or physical CAN-FD certification is made.

## Optional desktop branding and vendor inputs (board kit v0.3)

The YMBOT brain logo is downloaded, not bundled or relicensed by this repository. Source: https://www.ymbot.com/static/png/logo-CM8nhUEK.png ; SHA256 `c3fb34bb5b182375cbb30c5d9e2cc16808203e5b5b22a0781b7e1fbbaba635b6`. Trademark/artwork rights remain with their owner.

NoMachine, Mesa BSP bundles, matching vendor headers and native browser installers are not redistributed here. Supply the matching components and their source/license obligations as described in `docs/FIRST_BOOT.md`. ToDesk installer provenance/hash is in `board/assets/remote-packages.json`. The optional ToDesk password writer is a version-specific local configuration implementation tested with 4.8.5.1; it is not an official vendor API or a password-recovery tool and never decrypts pre-existing credentials.

## Static teaching Wiki build dependencies

The Wiki renderer uses markdown-it-py 4.0.0 and mdurl 0.1.2, both MIT-licensed, installed from PyPI into the build environment. Their source code is not bundled into the static HTML output. Upstream: https://github.com/executablebooks/markdown-it-py and https://github.com/executablebooks/mdurl . The Wiki CSS, browser JavaScript and build scripts are maintained in this repository under its license. No third-party fonts, analytics or runtime scripts are loaded by the site.
