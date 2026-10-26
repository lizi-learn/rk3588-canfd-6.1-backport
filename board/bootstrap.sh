#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Version-pinned launcher. Optimization and validation remain separate actions.
set -euo pipefail
version=v0.3.1
action=${1:-}
case "$action" in setup|optimize|verify|rollback|wifi|brand|repair-browser|todesk-password) shift;; *) echo "Usage: bash bootstrap.sh {setup|optimize|verify|rollback|wifi|brand|repair-browser|todesk-password} [arguments]" >&2; exit 2;; esac
cache_dir=${XDG_CACHE_HOME:-$HOME/.cache}/rk3588-board-kit/$version
if [ ! -d "$cache_dir" ]; then
  release_url=https://github.com/lizi-learn/ymbot-5io-system-optimization/releases/download/$version
  staging_dir=$(mktemp -d)
  trap 'rm -rf "$staging_dir"' EXIT
  archive=rk3588-board-kit-$version.tar.gz
  curl --fail --location --proto '=https' --proto-redir '=https' --retry 2 "$release_url/$archive" -o "$staging_dir/$archive"
  curl --fail --location --proto '=https' --proto-redir '=https' --retry 2 "$release_url/kit-SHA256SUMS" -o "$staging_dir/kit-SHA256SUMS"
  (cd "$staging_dir"; sha256sum --check kit-SHA256SUMS)
  mkdir -p "$(dirname "$cache_dir")" "$staging_dir/source"
  tar --no-same-owner -xzf "$staging_dir/$archive" -C "$staging_dir/source"
  mv "$staging_dir/source" "$cache_dir"
fi
python3 "$cache_dir/scripts/check_source.py"
if [ "$EUID" -eq 0 ]; then exec "$cache_dir/board/$action.sh" "$@"; fi
exec sudo "$cache_dir/board/$action.sh" "$@"
