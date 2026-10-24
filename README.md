# RK3588 CAN FD Linux 6.1 backport

面向 RK3588 / Linux 6.1.172 ARM64 的实验性 CAN FD 驱动回移项目。
驱动主体来自 Linux 上游；本项目提供旧内核 API 兼容、板级设备树示例、构建步骤和 CAN 专用验证工具。

**状态：experimental。已完成一台设备的编译、启动绑定和控制器内部硬件回环；外部 CAN 总线尚未接线验收。**
本仓库是第二个开源项目的源码仓库，不提供在线服务，也没有默认绿色健康状态或定时在线探测。

## 已完成的验证

| 项目 | 结果 |
| --- | --- |
| 设备 | RK3588 核心板 + LBM5-DIBAN-V01A 自研底板 |
| 系统 | Ubuntu 22.04 ARM64，Linux 6.1.172 |
| 模块 | `lbm5_canfd`；模块内版本 `1.0-experimental` |
| 普通 CAN | 名义速率 1 Mbps；两路内部硬件回环通过 |
| CAN FD+BRS | 仲裁 1 Mbps；数据 1 / 2 / 5 Mbps 内部硬件回环通过 |
| 正式测试量 | 重启前后各 8 组，每组 10,000 个应用发送帧，合计 160,000 帧 |
| 重启自动绑定 | 已通过；最终恢复 FD 1M / 5M，控制器回环关闭 |
| 外部收发器 / 接插件 / 线缆 | **尚未验证** |
| FD 数据 3 Mbps | 内部回环超时，未解决，未列为合格档位 |

500 kbps 是先前配置值，不是控制器上限。5 Mbps 指 FD+BRS 帧的数据阶段，仲裁和普通帧仍为 1 Mbps。
5M 内部通过不代表 3M 或其他档位也通过，不代表已探明整机物理最高速率。

## 来源与本项目改动

- 上游：[`torvalds/linux`](https://github.com/torvalds/linux)，固定提交
  `5b0764a53235d3c77e1ed674e836e1b3fe1a4b1f`。
- 原驱动作者及版权通知保留；上游包含基于 Rockchip 驱动的实现，不能将本项目表述为从零自主研发全部驱动。
- 本项目将较新的 CAN 结构、队列、时间戳和平台 remove 等 API 回移到 6.1；模块改名隔离。
- 保留上游 RK3588 RX FIFO 位域、勘误 5/6 和 TDC=0 的处理。
- CAN 时钟固定为 300 MHz；验证设备通过已有 CPLL 分频实现，未改变 PLL 频率。
- 两路设备树示例只改 compatible 与 assigned-clock-rates，原 CAN 引脚复用插件仍需启用。

原始源码、来源 URL、SHA256 和兼容辅助函数的参考原文均保存在仓库中，见
[THIRD_PARTY.md](THIRD_PARTY.md) 与 [PROVENANCE.json](PROVENANCE.json)。

## 构建

先取得与运行内核**完全匹配**的厂商内核头文件、构建配置及符号版本。
仅同为 Linux 6.1 或 RK3588 并不足以证明 ABI 匹配；本项目未验证通用发行版 6.1 或其他 BSP。

```sh
sudo apt-get install build-essential device-tree-compiler python3 iproute2 can-utils
uname -r
test -d /lib/modules/$(uname -r)/build
make KDIR=/lib/modules/$(uname -r)/build CAN_CC=aarch64-linux-gnu-gcc
make overlay
make check
modinfo driver/lbm5_canfd.ko
```

验证设备使用 GCC 11.4.0 和厂商 `linux-headers-6.1.172`。`make check` 只做离线来源与交付检查，不能替代内核编译或硬件通信测试。
如果交叉编译，应明确设置目标内核构建目录和对应编译器；不要用开发电脑自己的内核头文件。

## 安装与使用

详细步骤见 [docs/INSTALL.md](docs/INSTALL.md)。先为目标设备新建文件备份，再安装模块、设备树插件并重启。
不提供会自动覆盖整份启动文件的一键安装脚本。该仓库不调整 UART、远程桌面、网络、音频或显示设置。

```sh
# After installation and reboot; these settings interrupt CAN traffic.
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000 sample-point 0.8 \
  dbitrate 5000000 dsample-point 0.8 fd on loopback off \
  listen-only off berr-reporting on restart-ms 100
sudo ip link set can0 txqueuelen 128
sudo ip link set can0 up
ip -details -statistics link show can0
```

对 `can1` 重复设置。示例未创建持久化参数服务；重启后的速率由目标设备自己的开机配置决定。
如果原系统已有配置服务，需要同步其默认值，避免互相覆盖。

## 验证工具

先停止业务程序，并确保没有其他进程配置这两路 CAN。

```sh
sudo python3 tools/lbm5-canfd-test --internal --count 10000 \
  --json /tmp/canfd-internal.json
```

工具固定检查 `can0 -> fea60000.can`、`can1 -> fea70000.can` 及 `lbm5_canfd` 驱动名。
内部模式测试经典 1M，以及 FD 数据 1M / 2M / 5M；分别核对硬件内部 RX 与发送完成回显。
**结束时固定恢复正常 FD 1M / 5M，不恢复调用前的业务速率；测试后应重新核对业务配置。**
使用普通 Python 执行，不要加 `-O`，工具用 `assert` 做验收判定。

外部交叉模式已经编写，**尚未实际执行**：

```sh
# Only after correct wiring, termination, and a clear physical test bus.
sudo python3 tools/lbm5-canfd-test --cross --count 10000 \
  --json /tmp/canfd-cross.json
```

此模式固定 FD 仲裁 1M / 数据 5M，两个方向各发指定帧数，要求软件 CAN 网关为空。
接线条件和验证边界见 [docs/VERIFICATION.md](docs/VERIFICATION.md)。

## 适用范围与维护

- 仅 RK3588、上述两路映射和指定厂商内核完成验证。源码保留其他上游 compatible 条目，但不构成对 RK3568 等平台的适配承诺。
- 未验证休眠恢复、多节点仲裁、长期负载、温度范围、EMC、线束极限和外部 5M 通信。
- 内核升级后重新编译、检查符号 ABI、重启绑定并复测。
- 3M 超时记录在 [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)，不以低速率推断必然可用。
- 开源发布不代表原厂认证或生产放行。

## License

GPL-2.0-only，见 [LICENSE](LICENSE)。保留 Linux / Rockchip / Pengutronix 等原作者通知。
公开内容包含驱动及工程适配源码，不包含设备登录信息、原始板卡图纸或私有运行日志。
