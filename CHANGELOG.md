# Changelog

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
