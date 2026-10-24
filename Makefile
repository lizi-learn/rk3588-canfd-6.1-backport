# SPDX-License-Identifier: GPL-2.0-only
KDIR ?= /lib/modules/$(shell uname -r)/build
CAN_ARCH ?= arm64
CAN_CC ?= aarch64-linux-gnu-gcc
.PHONY: all modules overlay check clean
all: modules
modules:
	$(MAKE) -C "$(KDIR)" M="$(CURDIR)/driver" ARCH="$(CAN_ARCH)" CC="$(CAN_CC)" modules
overlay:
	mkdir -p build
	dtc -@ -I dts -O dtb -o build/rk3588-lbm5-canfd-overlay.dtbo dts/rk3588-lbm5-canfd-overlay.dts
check:
	python3 scripts/check_source.py
clean:
	$(MAKE) -C "$(KDIR)" M="$(CURDIR)/driver" clean
	rm -rf build
