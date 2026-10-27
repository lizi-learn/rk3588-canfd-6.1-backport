# 接手新机到交付：v0.3.1

适用固定组合：LBM5-DIBAN-V01A 底板、LubanCat-5IO/5IOB RK3588、Ubuntu 22.04 ARM64、厂商 Linux 6.1.172。两路 RS485 均焊接；未焊第二路的旧板传 `--rs485-2 off`。桌面用途为不接显示器的远程访问。不同内核、不同底板或纯 Ubuntu 镜像需要单独适配。

## 1. 接手、联网

通过当前可达的有线地址 SSH 登录，核对 `uname -a` 和 `/proc/device-tree/model`。初始账户通常为 `cat`，脚本从 sudo 调用者或 UID1000 识别，也可显式指定 `--source-user cat`。

需要配无线网时先执行 `sudo ./board/wifi.sh`，通过隐藏输入设置 Wi-Fi 口令；用 `nmcli device show` 取得地址，并从管理电脑验证该地址的 SSH。脚本不扫描/复制另一台电脑的网络凭据，不写死 IP。

```sh
git clone --branch v0.3.1 https://github.com/lizi-learn/ymbot-5io-system-optimization.git
cd ymbot-5io-system-optimization
python3 scripts/check_source.py
sudo ./board/setup.sh --carrier lbm5-diban-v01a --dry-run
```

## 2. 一键配置

相同厂商 BSP 已有 Mesa 26.2.3、内核头文件和 NoMachine 时：

```sh
sudo ./board/setup.sh --carrier lbm5-diban-v01a --reboot
```

按提示隐藏输入 ToDesk 固定密码、当前系统密码、新系统密码及确认。公开脚本没有统一默认口令；部署时输入约定口令即可。本次实机的系统密码和 ToDesk 密码已另行设置、校验，口令不会出现在仓库、日志、参数或环境变量中。已有设备仅更新配置、保留密码时加 `--keep-password`。

流程包括：

1. 核对 BSP、原账户、目标账户冲突和输入哈希；缺少 GNOME 时通过 Ubuntu 软件源安装 GNOME/GDM、Dock、控制中心、录音机和依赖。
2. 在目标机用匹配的厂商头文件编译 CAN 回移模块；合并全部 DT 插件后核对两路 CAN/UART 节点。默认普通 CAN 1M、485 115200/8N1，第二路启用。
3. 配置 GNOME X11、1920×1080 无屏输出、Panfrost/Mesa 路径、Chromium 会话后端、禁空闲休眠、NoMachine/ToDesk、禁 NoMachine 音频转发；移除无网络文件系统依赖时的开机 network-online 等待，关闭 Wi-Fi 省电。
4. 安装 GNOME Sound Recorder，仅安装和启动检查，不自动录音。使用官网原始蓝色大脑 logo，黑底居中，并设置头像；补齐“关于”页面和备用 Plymouth 图标，详见 [BRANDING.md](BRANDING.md)。
5. 通过独立 root 服务停止旧桌面、迁移账户和主目录到 `ymbot`，保留 UID/GID、附加组、密码、浏览器资料与 SSH 密钥；主机名改 `ymbot`。清理已经确认失效的 Chromium singleton 符号链接，保留归档。旧登录名消失，旧主目录保留兼容链接。
6. 配置完成后，带 `--reboot` 则一分钟后重启；未带则手动重启。原 SSH 在改名期间断开属于预期。重连用 `ssh ymbot@实际IP`，使用刚输入的新系统密码。

配置在独立 root 服务中运行，SSH 断开不会终止工作。状态命令：

```sh
sudo ./board/setup.sh --status
# 启动时会给出完整 unit 名称，可查看日志
sudo journalctl -fu rk3588-setup-实际编号
```

配置成功只表示配置写入成功，不表示物理通信验收。优化不发送 CAN/485 帧。状态中的 `hardware_acceptance` 保持未执行，不能作为硬件绿灯。

### 镜像缺少组件时

本次新机接手时已预装 GNOME、Mesa 26.2.3、NoMachine 和配套头文件。新入口支持缺少 GNOME 的安装分支；该分支只做离线检查，尚未在全新刷机镜像重装验证。实机已验证的是相同 BSP 的重复执行、密码修改、浏览器修复及独立健康检查。

Mesa、内核头文件与 NoMachine 不从另一台机器复制身份/私密配置，也不猜测下载链接。缺少时由镜像/厂商提供下列输入，脚本校验后安装；没有输入则在预检阶段停止：

| 组件 | 输入参数 |
| --- | --- |
| Mesa 26.2.3 | `--mesa-bundle /绝对路径/mesa.tar.gz --mesa-sha256 实际SHA256`，归档只有 `mesa-26.2.3/`，含 `lib/aarch64-linux-gnu/dri/libdril_dri.so`；必须适配此 BSP，来源方保留许可证/对应源码 |
| 精确匹配的内核头文件 | `--headers-deb /绝对路径/headers.deb --headers-sha256 实际SHA256`；厂商包名 `linux-headers-6.1.172`，提供 Makefile、生成配置和 Module.symvers；相同版本号不保证 ABI |
| NoMachine 服务端 | `--nomachine-deb /绝对路径/server.deb --nomachine-sha256 实际SHA256`；包名 nomachine、ARM64、适用许可；项目不托管安装器/许可，也不以客户端代替服务端 |
| 原生 Chromium | `--chromium-package-dir /绝对路径/目录`；包含适配 BSP 的 chromium、chromium-common、chromium-sandbox .deb 及 SHA256SUMS；保留已装版本，不自动替换为 Ubuntu snap 过渡包 |
| 离线 ToDesk | `--remote-package-dir /绝对路径/目录`，文件名/哈希见 `board/assets/remote-packages.json` |
| 离线官网 logo | `--logo-file /绝对路径/logo.png`，锁定原文件 SHA256，见 `board/setup.py` |

ToDesk 缺失时安装固定 SHA256 的 4.8.5.1 ARM64 社区镜像包，明确不是厂商托管地址。固定密码写入逻辑只适配实测 4.8.5.1 格式，由本机二进制行为确认，不是厂商承诺的稳定 API；保留设备 ID，禁用临时密码，并核对写入后的新密文。其他版本需 `--keep-password`，在厂商界面配置。新系统密码通过用户的 `passwd`/PAM 路径更改，保留现有登录密钥环。自动登录后密钥环仍可能需要本次登录解锁；不删除密钥环、不降低浏览器密码存储保护。

## 3. 独立验证与接线

重启并重连后，在仓库目录执行：

```sh
# 不发数据：服务、接口配置、GPU、分辨率、账户/logo/应用是否安装
sudo ./board/verify.sh
# 只有停止业务、按说明正确对插之后才执行物理收发
sudo ./board/verify.sh --physical
```

CAN-A/B 只连 H、L、GND，4 脚 24V 不接；485 两个独立 UART 的 A、B、GND 对接，电源脚不接。第二路实际引出和终端由硬件人员核实；详细针脚及原理图限制见 [BOARD_KIT.md](BOARD_KIT.md)。健康检查不发帧，不录音，也不把服务存在/密码配置存在认定为完整远控交互。

普通 CAN 默认 1M。`--can-mode fd5m` 只供隔离台架研究：仲裁 1M、FD+BRS 数据阶段 5M，稳定性仍未通过。30 分钟压测收齐 12,386,944 帧，但扩展帧/混合负载有总线和 FIFO 异常；不自动提升默认速率。485 默认115200。2026-10-25历史装配曾在1.5M持续通过；2026-10-27换收发器后复测为1M持续通过、1.5M至4M持续失败，详见[分次速率记录](faq/rs485.md)。

## 4. 浏览器打不开时

改主机名后，浏览器旧 `SingletonLock` 可能仍写着旧主机名。先正常退出全部 Chromium，再运行：

```sh
sudo ./board/repair-browser.sh          # 检查，不改动
sudo ./board/repair-browser.sh --apply  # 仅清理证明确已失效的本地 singleton 链接
```

有活跃浏览器、活跃 socket、共享文件系统、异常文件类型时拒绝清理。不删除书签、历史、密码、整个个人资料。若出现登录密钥环提示，输入密钥环口令解锁；这与资料锁和 X11/Wayland 后端是不同检查。

单独更新 ToDesk 固定密码：`sudo ./board/todesk-password.sh`，通过隐藏输入提交，服务会短暂重启；不输出口令。配置读回不能替代对端密码登录测试。

## 5. 备份与恢复范围

优化、品牌和账户迁移各自记录 root 私有备份，状态 JSON 给出路径。`board/rollback.sh` 用于对应优化/品牌配置备份；不会卸载软件或恢复旧密码。账户迁移出错会在 root worker 内尝试反向迁移；`identity.json` 标记 `rolled-back` 或 `rollback-incomplete`。不要把账户迁移备份直接当作通用 rollback 的输入：它不会撤销 usermod，需在维护 SSH/串口控制台下按状态反向迁移。

断电中断、用户/主目录冲突、受限 SSH 用户规则或另挂载主目录都不属于已验证的自动迁移范围。保留镜像/厂商恢复手段；不复制静态 `/etc/shadow` 覆盖系统账户数据库。私有备份可能包含应用凭据，只保留在目标机 root 目录，不上传 GitHub。
