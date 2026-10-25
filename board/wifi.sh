#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
read -r -p 'Wi-Fi SSID: ' ssid
[ -n "$ssid" ] || exit 2
# NetworkManager asks for the password without putting it in argv or this script.
nmcli --ask device wifi connect "$ssid"
nmcli -f GENERAL.DEVICE,GENERAL.STATE,IP4.ADDRESS device show wlan0
