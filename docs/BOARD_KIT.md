# LBM5-DIBAN-V01A 操作说明（增量优化入口）

> v0.3 从新机接手、账户/主机名、密码、logo、录音机及浏览器修复，请先看 [FIRST_BOOT.md](FIRST_BOOT.md)。本页说明保留的 optimize 增量入口与接线。

## 适用条件

实机为 RK3588 + LBM5-DIBAN-V01A 自研底板，Ubuntu 22.04.5 ARM64，LubanCat-5IOB BSP、Linux 6.1.172（2026-10-17 构建）。两路 MAX13488 已焊接，UART4M2 / UART7M2 对应 RS48_1 / RS48_2。仅适用于无实体显示器的远程桌面用途。

这是该 BSP 的增量配置工具，不是刷机镜像或通用 RK3588 安装器。要求镜像已含 GNOME/GDM 和 `/opt/mesa-26.2.3` GPU 组件，可在线或在离线用户 DConf 中初始化偏好。仅相同内核版本号不足以证明二进制 ABI 相同；CAN 模块在目标机使用配套厂商头文件现场编译，modpost/编译失败必须停止。

NoMachine 9.2.18 服务端已预装的设备保留原版本。缺少服务端时，先从厂商取得适用许可的 ARM64 **服务端**安装包，执行优化时增加 `--nomachine-deb /绝对路径/安装包.deb`；免费客户端包不能替代服务端。本项目不托管或绕过商业许可。历史 9.2 下载链接已失效，不承诺自动取得旧包。

ToDesk 已安装则保留版本、设备 ID 和密码。缺少时下载锁定 SHA256 的 4.8.5.1 ARM64 社区包（Spark Store/山东大学镜像，非厂商直链），来源和哈希见 `board/assets/remote-packages.json`。也可用 `--remote-package-dir /绝对路径/目录` 提供同名同哈希安装包。首次安装应在 ToDesk 安全设置中设置固定密码；本脚本不复制其他设备凭据，也不重置已有密码。

## 接手及网络

1. 先通过已知有线地址 SSH 登录并核对板型、内核、底板装配及接口空闲状态。不要把 SSH/Wi-Fi/远程桌面密码写入 Git。
2. 如需配 Wi-Fi，运行 `sudo ./board/wifi.sh`，在终端输入 SSID 与 nmcli 密码提示；`nmcli -g IP4.ADDRESS device show wlan0` 查看实际地址，再从管理电脑验证 SSH。此步骤与优化分开，不写死网段。
3. 下载本仓库的固定版本并核对来源。以下命令均在目标板仓库根目录执行：

```sh
git clone --branch v0.3.1 https://github.com/lizi-learn/ymbot-5io-system-optimization.git
cd ymbot-5io-system-optimization
python3 scripts/check_source.py
sudo ./board/optimize.sh --carrier lbm5-diban-v01a --dry-run
```

## 一键优化（默认普通 CAN 1M）

```sh
sudo ./board/optimize.sh --carrier lbm5-diban-v01a
sudo reboot
```

两路 RS485 默认 115200/8N1，自动方向。未焊接备用 RS48_2 的旧板需加 `--rs485-2 off`。默认从调用者/ymbot/UID1000 自动识别；需要覆盖时加 `--user 用户名`。优化会中断后续业务，先停止接口业务程序。脚本不主动发送总线帧，不自动重启，不把“写完配置”当作验收通过。

配置涉及：活动 U-Boot 板型文件；CAN/UART pinmux；开机接口服务；1080p 内置 EDID、关闭空置 HDMI1；GNOME X11 自动登录；已有 Mesa/Panfrost 路径；Chromium 会话后端；禁空闲休眠/锁屏；保留联网的同时移除无远程文件系统时的 network-online 启动等待；关闭 Wi-Fi 省电；启用远程桌面服务，禁用 NoMachine 音频转发。

自动登录和禁锁屏适合本次封闭设备用途。部署到其他场所前按访问控制要求调整。保留现有登录密钥环，不删除或重置。原密钥环口令与登录口令不一致时，Chromium 仍可能提示解锁。

备份写入 `/var/backups/rk3588-board-kit/时间戳/`，配置结果为 `/var/lib/rk3588-board-kit/last-optimize.json`（root 可读）。失败会打印备份路径，不会输出成功验收。

## 独立验证

```sh
# 不发总线帧：服务、GPU、显示、速率、别名、音频、固定密码是否存在
sudo ./board/verify.sh

# 硬件按下面接线并停止业务后，才执行实收实发
sudo ./board/verify.sh --physical
```

验证脚本不安装软件、不改启动项、不改变 CAN 模式和速率；RS485 为测试临时切换波特率并在 finally 恢复原 termios。仅 `--physical` 发数据。失败返回非零，结果 JSON 在 `/var/lib/rk3588-board-kit/verification-时间戳.json`，默认 0600。物理测试抛出异常时，为停止未获确认的持续重发，脚本将 CAN 置 down；排除故障后 `sudo systemctl restart lbm5-can.service` 再验证。先检查原因，不把重启后计数清零当作测试通过。

健康检查的通过只适用于所列检查。NoMachine/ToDesk 的对端登录、鼠标键盘和完整交互仍需远程客户端验收，脚本不会把服务进程存活当作完整远控通过。

### 台架接线

断电接线后复核电源脚。CAN-A（J46/J47 同一路）与 CAN-B（J50/J51 同一路）接 1↔1 CANH、2↔2 CANL、3↔3 GND；**4 脚 24V 不接**。终端按实际电阻装配核实，两端各 120Ω 时断电 H-L 应约 60Ω，不额外盲目并联终端。

RS48_1（UART4）A↔RS48_2（UART7）A、B↔B、GND↔GND。J52/J53/J54 是 RS48_1 的并联接口：2=A、3=B、4=GND；**1 脚 5V 不接**。它们不是两路独立串口，不能用 J52↔J53 冒充双通道验证。

图纸第 17 页的第二路信号为 RS485_2_A/B，可经 R458/R457 路由到 J71 的 A3/A2（图纸标注 NC，需核对实装）。RS48_2 应由硬件同事确认实际引出点；不要把这个自定义 Type-C 信号映射当作标准 USB 串口口，也不要把普通 USB 设备接入用作 485 测试。原理图原件不随本仓库分发。

台架测试排除硬件内部回环、SocketCAN 本地回显和软件 CAN 网关，逐帧/逐字节核对对端接收及错误计数增量。485 发送端存在物理自回显，只统计另一 UART 接收作为跨口成功；业务协议需处理本地回显和半双工换向。

## 实验性 CAN FD 1M/5M（稳定性未通过）

```sh
sudo ./board/optimize.sh --carrier lbm5-diban-v01a --can-mode fd5m
sudo reboot
sudo ./board/verify.sh --physical
```

5M 是 CAN FD+BRS 的数据阶段，仲裁仍 1M，普通 CAN 上限按本配置为 1M；不能让普通 8 字节经典帧变成 5M。历史单次零错误、但重启重复测试失败。发布复测全部 43,202 帧收到，仍新增总线错误 49/45；因此不能按稳定 5M 验收。以下 profile 仅供隔离台架研究复现：CAN clock 300 MHz，仲裁采样点 80%、SJW16；数据 BRP10、6 TQ/bit、采样点 83.3%、SJW1、TDC=0。自动 BRP2/80%、BRP10、BRP12、BRP20 的已知失败均留档，不能把此前单次通过写成稳定合格。

两种模式均原生编译并安装 `lbm5_canfd.ko`、新增 compatible/300MHz 插件及模块自动加载，重启后检查真实绑定。不强制 vermagic、不热解绑正在运行的控制器。普通 1M 与 FD 5M 均使用该 RK3588 专用回移驱动，区别是是否启用 FD 数据阶段；普通 1M 也需目标内核头文件。原厂 rk3568_can 在本次重复验证中曾出现 1 帧重复、1 帧缺失，因此不作为发布默认驱动。专用回移驱动也未消除硬件勘误：后续一轮完整 24,002 帧收到，但 can1 的 tx_errors / tx_extended_as_standard_errors 同增19；记录为有恢复异常，不能宣称已零错误验收。

恢复普通 1M：重新执行不带 `--can-mode fd5m` 的默认优化命令并重启，再独立验证。继续使用专用回移驱动、300MHz 时钟和仲裁 SJW16，关闭 FD 模式。只有回退原始备份才恢复原厂驱动。

## 备份回退

```sh
sudo ./board/rollback.sh /var/backups/rk3588-board-kit/实际时间戳 --dry-run
sudo ./board/rollback.sh /var/backups/rk3588-board-kit/实际时间戳
sudo reboot
```

回退核对备份哈希，恢复记录的文件、服务开机状态、Wi-Fi 省电和 GNOME 偏好。保留安装的软件包；不会卸载远程桌面或复制其他设备身份。配置备份可能包含应用私密信息，只保留本地 root 目录，勿公开上传。

## 留档

分别保存基线、优化结果、重启后的健康 JSON、接线照片/线长/终端实测和物理测试 JSON。`systemd-analyze time` 与 GNOME/Wi-Fi 就绪日志是不同口径，不等同于电源上电至远程可操作时间。当前发布报告明确列出未测项目；本台通过不替代多板、长线、EMC、温度和长时间压力验证。

维护者可用安装reportlab与文泉驿正黑字体的Python环境运行 `python3 docs/build_reports.py` 生成PDF。它只读取已发布脱敏证据，不连接设备；无需在生产板上运行。
