# YMBOT 5IO 开发板系统优化

同事教学与查阅入口：**[在线 Wiki](https://ymbot-5io-wiki.pages.dev/)**。从新机配置、CAN/RS485 接线与验证，到无屏桌面、浏览器、Wi-Fi 和启动优化，按实机问题整理。源码仓库已更名为 [ymbot-5io-system-optimization](https://github.com/lizi-learn/ymbot-5io-system-optimization)。旧仓库地址由 GitHub 重定向，历史版本标签和发布归档保留。

RK3588 / Linux 6.1.172 的实验性 CAN FD 驱动回移，以及 LBM5-DIBAN-V01A 自研底板的配置与独立验证工具。驱动主体来自 Linux 上游，本项目完成 6.1 API 兼容、板级适配、位时序调优及实机验证，保留原作者版权与 GPL-2.0-only 许可。

**v0.3.1：增加从接手同款 BSP 新机开始的配置入口、ymbot 账户/主机名、大脑 logo、录音机、隐藏密码设置和 Chromium 改名锁修复；补齐“关于”页面图标与启动标志审查。优化与验证继续分开。CAN FD 5M 稳定性仍未通过，不显示默认硬件绿灯。**

| 实测项目（分次记录） | 结果 |
| --- | --- |
| 普通 CAN 1M | 数据完整的多次记录之外，仍有原厂丢失/重复、回移驱动勘误6恢复失败记录，未完成零错误验收 |
| FD+BRS 1M/5M，30分钟 | 12,386,944 帧全部收到；标准64字节帧两个方向各600秒零错误，扩展/混合负载累计每口 bus_error +6、一个 RX FIFO 异常，严格失败 |
| RS485 2026-10-25历史装配 | 1.5M baud 连续双向20MiB+1000次换向通过；2M及以上持续失败 |
| RS485 2026-10-27换芯片复测 | 1M持续20MiB+1000次换向通过；1.5M至4M持续失败；4M仅短测通过；默认115200，见[新旧对照](docs/RS485_CHIP_SWAP_20261027.md) |
| 启动 systemd 指标 | 基线60.614s，优化后多次6.6–7.2s，改名重启6.786s；Wi-Fi约23–24s，不等同上电到远程可用 |
| 无屏桌面 / GPU | GNOME X11、1080p、Mali-G610 Panfrost accelerated=yes |
| 账户 / 桌面 / 应用 | ymbot 登录和主机名、官网大脑logo、GNOME录音机；Chromium旧主机名锁已修复并确认网页加载 |
| 远程桌面 | NoMachine/ToDesk 服务、固定密码配置；配置读回不等于对端完整交互验收 |

证据见 [board/evidence](board/evidence/)。CI 只做离线检查，不连接设备，不改变硬件验收结论。

## 常见问题与教学 Wiki

- [为什么有两个 Wi-Fi？](docs/faq/wifi.md)：同一块 RTL8852BE、同一个 phy0 的 wlan0 与 p2p0；后者由驱动预创建供 P2P 使用，并非第二块无线网卡。当前未连接，不影响 wlan0 已建立的连接；没有为了隐藏图标而关闭接口。
- [普通 CAN / CAN FD、1M / 5M 怎么区分？](docs/faq/can.md)：500k 是配置值；FD 5M 是数据阶段速率。收齐帧仍可能发生总线错误，不能用零丢帧替代严格验收。
- [485 能跑多快？两路分别在哪？](docs/faq/rs485.md)：UART4 / UART7；历史1.5M通过，换芯片后本次持续通过最高已测1M，两者均不是物理极限。
- [Chromium 打不开、llvmpipe 和无屏桌面](docs/faq/desktop.md)、[启动耗时的正确口径](docs/faq/boot.md)、[系统图标与开机画面](docs/BRANDING.md)。

[完整问答索引](docs/FAQ.md) · [从接手到交付操作单](docs/FIRST_BOOT.md) · [Wiki 维护与 Cloudflare 发布](wiki/README.md)。后续有价值的问题补入 Markdown，保留实测日期、证据和未验证范围，再构建发布；网页与仓库使用同一份正文。

## 新机一键配置，独立验证

先看 [从接手到交付操作单](docs/FIRST_BOOT.md)。固定适用：LBM5-DIBAN-V01A、LubanCat-5IO(B) BSP、Ubuntu22.04 ARM64、Linux6.1.172。接手的实机镜像已含 Mesa26.2.3、匹配头文件和 NoMachine；缺少时需提供厂商/镜像组件及哈希，脚本不猜测下载链接。缺 GNOME 时支持安装，但全新刷机重装分支尚未实机验收。

```sh
curl -fsSL https://raw.githubusercontent.com/lizi-learn/ymbot-5io-system-optimization/v0.3.1/board/bootstrap.sh -o /tmp/rk3588-kit.sh
# 一键配置；按提示隐藏输入系统和 ToDesk 新密码；完成后重启
bash /tmp/rk3588-kit.sh setup --carrier lbm5-diban-v01a --reboot
```

改名时 SSH 会断开，root 服务继续运行。重连 `ssh ymbot@实际IP` 后独立验证：

```sh
# 健康检查，不发总线数据
bash /tmp/rk3588-kit.sh verify
# 停止业务并正确对插以后，实际验证 CAN/485
bash /tmp/rk3588-kit.sh verify --physical
```

已有设备保留密码重复配置：`setup --carrier lbm5-diban-v01a --keep-password`。初始账户默认自动识别，也可 `--source-user cat`；第二路485未焊接用 `--rs485-2 off`。公开脚本不含统一默认密码、Wi-Fi凭据或设备远控身份。

Git clone 用户执行 `sudo ./board/setup.sh --carrier lbm5-diban-v01a`；增量优化仍用 `board/optimize.sh`，验证仍用 `board/verify.sh`。`--dry-run` 只预检，优化和配置不发送总线帧。回退与缺少组件时的参数见 [操作单](docs/FIRST_BOOT.md) 和 [接线/增量说明](docs/BOARD_KIT.md)。`docs/pdf/` 保留 v0.2 历史报告及2026-10-27换芯片复测补充报告，当前配置入口以 v0.3 操作单为准。

## 系统标志

新机 setup 自动替换 GNOME“关于”页面浅/深色图标，以及根文件系统里备用的 Plymouth 图标。已有 v0.3.0 设备可运行 `brand --apply`，见 [标志与启动审查](docs/BRANDING.md)。当前快速启动仍保持 Plymouth 禁用、内核 Linux logo 禁用；未刷写 U-Boot，未实屏确认其早期画面。

## 5M 的关键结果

500k 是配置值，不是上限。普通 CAN 已实测 1M；5M 只指 CAN FD+BRS 数据阶段，仲裁保持 1M。

自动位时序 BRP2 / 数据采样 80% 曾出现“全部帧收到、错误增加”，不能算合格。历史零错误单次使用的参数为 CAN 时钟 300MHz、仲裁 1M / 采样80% / SJW16，数据 BRP10 / 6TQ / 采样83.3% / SJW1，TDC=0。实验性 fd5m 入口保留这组参数供复现，重启复测仍有错误；BRP12/20 的补充探测也未解决。应检查实装收发器、终端、接地、线束和示波器波形，未取得这些证据前不归因于单一硬件或软件原因。

未探明整机物理最高速率。此前旧板 3M 内回环超时依然保留为未解决问题；本次没有重新宣称 3M 通过。没有多节点仲裁、EMC、长线、温度或长时间寿命测试。

## 驱动构建与来源

上游固定提交 `5b0764a53235d3c77e1ed674e836e1b3fe1a4b1f`，来源及兼容引用见 [THIRD_PARTY.md](THIRD_PARTY.md)、[PROVENANCE.json](PROVENANCE.json)。回移覆盖 CAN 结构、队列、时间戳和平台 remove API，保留 RK3588 RX FIFO 位域、勘误5/6和 TDC=0；模块隔离名 `lbm5_canfd`。不能把项目描述成从零自研驱动。

```sh
# 在目标板，使用与正在运行内核完全匹配的厂商头文件/config/Module.symvers
sudo apt-get install build-essential gcc-aarch64-linux-gnu device-tree-compiler
make KDIR=/lib/modules/$(uname -r)/build
make overlay
make check
```

只同为 6.1.172 不足以保证 ABI。不能跳过编译错误、强制 vermagic 或复用另一内核的 .ko。普通 1M 和 FD 5M 均使用 RK3588 专用回移驱动（FD 可关闭）。原厂 rk3568_can 在封装复测时曾出现扩展帧重复/缺失，保留该失败记录；不作为新发布默认驱动。当前板级入口现场编译，不发布可随意跨 BSP 装载的模块二进制。

## 历史材料

根目录 `evidence/verification-summary.json` 是 v0.1.0 **另一台旧设备**的 160,000 帧内部硬件回环记录，外部未接线的历史事实不改写。[原手动安装说明](docs/INSTALL.md)、[旧验证工具与边界](docs/VERIFICATION.md)、[已知问题](docs/KNOWN_ISSUES.md) 作为驱动开发参考保留；新板的外部 5M 请使用 `board/` 工具及最新操作说明，避免旧工具自动选择的时序。

GPL-2.0-only，见 [LICENSE](LICENSE)。本仓库不含原始私有图纸、网络口令、远程桌面身份或原始私密日志。
