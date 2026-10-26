# 桌面、浏览器与音频排查

实机环境：Ubuntu22.04、GNOME X11、无实体显示器、Mali-G610 Panfrost。整理日期：2026-10-26。

## Chromium 为什么打不开

这里先后遇到过两种原因，应根据日志分别处理。

**会话后端不一致。** Chromium 曾强制使用 Wayland，而 GNOME 正在使用 X11。现有配置 `/etc/chromium.d/zz-session-platform` 根据实际会话选择后端，并使用适配 Mali 的 ANGLE GLES 路径。当前无屏远程桌面使用 X11；没有必要仅为浏览器强切整套桌面。保留 Chromium sandbox。

**改主机名后遗留资料锁。** 从旧主机名改为 `ymbot` 后，Chromium 的 `SingletonLock` 仍指向旧主机名和已消失进程。确认没有活跃浏览器、有效 socket，且资料在本地文件系统后，只归档并清理已失效的三个 singleton 符号链接。书签、密码、历史和个人资料均保留；修复后实际网页加载已验证。

```sh
# 先正常退出 Chromium，在仓库目录执行
sudo ./board/repair-browser.sh          # 仅检查
sudo ./board/repair-browser.sh --apply  # 符合条件时归档、清理失效链接
```

工具遇到活跃进程/socket、共享文件系统或异常文件类型会拒绝清理。不要把删除整个浏览器资料目录当作常规修复。

## 密钥环提示与浏览器故障一样吗

自动登录可能没有解锁 GNOME 登录密钥环。系统密码通过 PAM 修改并保留密钥环，当前登录可能仍需输入密钥环口令。它与显示后端或资料锁是不同问题；不删除密钥环，也不把密码存储降为明文以消除提示。

## llvmpipe 是什么意思

llvmpipe 表示 Mesa 使用 CPU 做软件图形渲染。桌面仍可能显示，但会增加 CPU 占用，并可能影响动画和远程桌面流畅度。

本机优化后的实测已是 **Mali-G610 Panfrost，accelerated=yes**，使用适配当前 BSP 的 `/opt/mesa-26.2.3` 组件。早先的 llvmpipe 描述是当时状态，不是当前结论。GPU 渲染加速与远控视频编码加速也不是同一件事。

```sh
# 检查已配置 GPU、桌面、分辨率和服务；不发送 CAN/485 数据
sudo ./board/verify.sh
```

## 不插显示器，远程桌面为什么还能用

当前针对无屏用途固定 GNOME X11、内置1080p EDID、HDMI0 1920×1080@60，并关闭空置 HDMI1，提供可捕获的桌面输出；配置自动登录和本用途下的禁空闲休眠/锁屏。换成实体显示器用途时应重新评估显示配置。

NoMachine/ToDesk 的服务运行和固定密码配置已检查，但配置读回不是对端完整交互验收。新部署应从远程客户端实际登录，确认鼠标、键盘、应用启动、断开重连。安装缺少的 NoMachine 服务端需厂商有效安装包和适用许可；客户端包不等于服务端。

## NoMachine 音频与录音机

按本设备用途，NoMachine 音频转发已禁用：`EnableAudio=0`、`AudioInterface=disabled`。这不会证明物理声卡、麦克风或扬声器本身是否正常。

GNOME Sound Recorder 42.0-1 已安装并打开界面；尚未完成麦克风实际录制、回放质量和硬件输入输出全链路验收。没有录音证据时，不能把软件安装成功写成音频通过。

操作入口和恢复范围见 [从接手到交付](../FIRST_BOOT.md)。
