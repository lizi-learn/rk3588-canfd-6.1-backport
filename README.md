# RK3588 CAN FD backport + LBM5 board kit

RK3588 / Linux 6.1.172 的实验性 CAN FD 驱动回移，以及 LBM5-DIBAN-V01A 自研底板的配置与独立验证工具。驱动主体来自 Linux 上游，本项目完成 6.1 API 兼容、板级适配、位时序调优及实机验证，保留原作者版权与 GPL-2.0-only 许可。

**v0.2.0：发布优化与独立验证工具，并保留真实通过和失败记录。5M FD 重启复测出现新增总线错误，稳定性未通过；不能称 5M 已优化完成。** 这是当前接线条件下的有限台架实测，不代表长线极限或生产认证。默认持久化配置为普通 CAN 1M。

| 实测项目（2026-10-25） | 结果 |
| --- | --- |
| 普通 CAN 1M | 历史 24,002 帧零错误；原厂复测丢失/重复各1，专用驱动复测数据完整但发现19次、最终26次勘误6恢复，零错误验收未完成 |
| FD+BRS 1M/5M | 历史单次 43,202 帧零错误；发布复测同样全部收到但新增总线错误 49/45，稳定性不通过 |
| RS485 UART4 / UART7 | 9600 / 115200 双向字节核对、200 次半双工换向通过 |
| 启动 systemd 指标 | 基线 60.614s；优化后 6.627s，后续7.151s，发布最终6.598s；Wi-Fi 就绪约日志时间轴 23–24s |
| 无屏桌面 / GPU | GNOME X11、1080p、Mali-G610 Panfrost accelerated=yes |
| 远程桌面 | NoMachine 9.2 服务认证与桌面流记录；ToDesk 4.8.5.1 服务/固定密码配置存在，对端完整交互未验收 |

公开的脱敏实测摘要、失败参数和复测记录见 [board/evidence](board/evidence/)。原始日志保存在本地，摘要包含原始文件 SHA256，便于核对。仓库不会默认显示“硬件已绿灯”；CI 只验证离线源码与构建，不连接设备。

## 两个独立入口

先阅读 [适用条件、接线和回退说明](docs/BOARD_KIT.md)。适用镜像须已含 GNOME/GDM、Mesa 26.2.3，以及现有 NoMachine 服务端或自行取得的适用许可安装包。ToDesk 缺失时使用锁定哈希的社区镜像包，来源在清单中明示。

```sh
git clone --branch v0.2.0 https://github.com/lizi-learn/rk3588-canfd-6.1-backport.git
cd rk3588-canfd-6.1-backport
python3 scripts/check_source.py

# 优化：默认普通 CAN 1M、两路 485 115200、无屏桌面与启动配置
sudo ./board/optimize.sh --carrier lbm5-diban-v01a
sudo reboot
```

重连后，在同一目录独立执行：

```sh
# 健康检查，不发总线数据
sudo ./board/verify.sh
# 已按说明正确对插并停止业务后，验证实际收发
sudo ./board/verify.sh --physical
```

仅研究复现 5M FD（当前稳定性未通过）时选择实验参数并重启，验证仍用同一个独立入口：

```sh
sudo ./board/optimize.sh --carrier lbm5-diban-v01a --can-mode fd5m
sudo reboot
# 重连并进入仓库目录
sudo ./board/verify.sh --physical
```

`--dry-run` 只查看优化计划；`--rs485-2 off` 用于第二路未焊接的旧板。工具不自动重启、不重置远程密码。配置备份支持 `board/rollback.sh`。详细 PDF 见 [发布附件](https://github.com/lizi-learn/rk3588-canfd-6.1-backport/releases/tag/v0.2.0) 与 `docs/pdf/`。

也可使用固定版本启动器（优化、验证依旧两条命令；下载包校验 SHA256）：

```sh
curl -fsSL https://raw.githubusercontent.com/lizi-learn/rk3588-canfd-6.1-backport/v0.2.0/board/bootstrap.sh -o /tmp/rk3588-kit.sh
bash /tmp/rk3588-kit.sh optimize --carrier lbm5-diban-v01a
# 手动重启并重连后
bash /tmp/rk3588-kit.sh verify --physical
```

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
