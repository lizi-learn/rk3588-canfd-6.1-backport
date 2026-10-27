# Changelog

## RS485 chip-swap retest - 2026-10-27

- Preserve the new hardware-state test separately: short sweeps pass through4M, sustained1.5M..4M fail with data mismatches and UART overruns;1M passes20MiB plus1000 turnarounds.
- Keep the same rate-test source hash and publish that physical-test tool for reproduction; restore115200 and retain prior1.5M historical evidence.
- Add a comparison report and Wiki lesson; do not infer a transceiver rating or unique root cause from this finite bench test.

## Repository rename - 2026-10-26

- Rename the repository to `lizi-learn/ymbot-5io-system-optimization`, matching the broader system-optimization scope.
- Update current setup, source and Wiki references; preserve existing release tags/assets and rely on GitHub redirects for historical links.

## Documentation / Wiki - 2026-10-26

- Present the project as YMBOT 5IO board system optimization, retaining repository URLs and published driver releases.
- Add a Cloudflare-hosted teaching Wiki from canonical Markdown, with full-text search, code copy, mobile navigation and explicit verification limits.
- Explain the actual RTL8852BE wlan0 / p2p0 mapping from a read-only audit, and consolidate CAN, RS485, desktop and boot questions.
- Publish the Wiki after source, offline board and static-site checks on main; keep credentials in repository Secrets and preserve all hardware failure records.

## 0.3.1 - 2026-10-25

- Replace the remaining GNOME About light/dark logo files with the original brain PNG.
- Replace inactive root-filesystem Plymouth fallback/watermark images, preserving fast boot: no splash enablement, initramfs rebuild or bootloader flash.
- Preserve vendor images with local dpkg diversions and support backup rollback.
- Add a standalone brand entry and read-only boot-logo audit; disclose unverified early firmware display instead of claiming a boot-screen visual pass.


## 0.3.0 - 2026-10-25

- Add received-board setup entry with GNOME/recorder package preparation, verified local vendor inputs, root worker, UID-preserving ymbot migration and original brain logo.
- Prompt for passwords without command-line or public defaults; change system password through user PAM; support version-specific ToDesk 4.8.5.1 fixed-password configuration/readback.
- Recover proven-stale local Chromium singleton links without deleting profile data; reject live browsers/sockets and shared filesystems.
- Detect desktop account dynamically and initialize preferences without a first GNOME login.
- Preserve 30-minute 5M FD strict failure (12,386,944 received frames) and RS485 sustained rate evidence (highest tested pass 1.5M).
- Test current-board repeat execution and independent health; fresh reimage installation and external ToDesk password login remain unverified.


## 0.1.0-experimental - 2026-10-25

- Initial public source release of the RK3588 CAN FD Linux6.1.172 backport.
- Module version remains the tested `1.0-experimental`; repository release version tracks packaging separately.
- Preserve fixed upstream references, GPL notices and Linux6.1 compatibility adaptations.
- Include two-port device-tree overlay, build instructions and controller-internal test utility.
- Publish selected-field verification summary: 160000 formal internal test frames across pre/post-reboot runs.
- Disclose unresolved 3M internal timeout and untested external CAN communication.
- No default green project-health badge or scheduled health probe.
