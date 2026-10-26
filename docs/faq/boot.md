# 启动耗时与优化

实机结果整理：2026-10-26。设备用途为只用远程桌面、不接实体显示器。

## 优化后到底快了多少

| 口径 | 实测 | 能说明什么 |
| --- | --- | --- |
| `systemd-analyze time` 基线 | 60.614秒 | 当次内核和用户态启动指标 |
| 同口径优化后多次 | 6.6–7.2秒 | 该指标明显缩短 |
| 账户改名后一次重启 | 6.786秒 = 内核2.601 + 用户态4.184 | 改名后配置仍有效；分项有舍入差 |
| Wi-Fi 日志就绪 | 约23–24秒 | 网络就绪晚于 systemd 指标 |
| 按电源到远程可操作 | 未完整测量 | 不能用6.786秒代替 |

systemd 的完成时点不等于 Wi-Fi 已连接，也不包含可独立解释的所有固件早期耗时。对同事报告“6.8秒启动”时应明确口径。参考 [systemd-analyze 文档](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html)。

## 这次调整了什么

- 无网络文件系统依赖时移除 NetworkManager wait-online 的开机等待；如果存在网络挂载则保留依赖检查，不能直接套用到所有机器。
- 无屏场景固定1080p EDID，减少空置 HDMI 的探测影响，关闭未使用的 HDMI1。
- 固定 GNOME X11 及适配的图形组件，维持自动登录、远程桌面服务和本用途的禁休眠。
- 关闭 Wi-Fi 省电以服务当前远程连接用途；网络实际关联耗时仍单独记录。

没有盲目删除相机、存储或未知硬件节点来换取较短数字。优化入口保留变更备份，详见 [接口与增量操作说明](../BOARD_KIT.md)。

## 如何重新测一次

```sh
systemd-analyze time
systemd-analyze critical-chain
systemd-analyze blame
journalctl -b -u NetworkManager --no-pager
```

先记录相同镜像/网络/供电下的基线，再应用优化，重启后用相同口径对比。`blame` 是服务耗时排名，不证明该服务一定处于启动关键路径；结合 `critical-chain` 和日志判断。

若要测“上电至远程可用”，需另录上电时点、SSH可达、Wi-Fi就绪和远程桌面能打开应用的时点。至少重复几次，记录网络和显示器状态，避免混用暖重启与冷启动。

## 和开机 logo 有关系吗

当前 Plymouth 禁用、内核未启用 Linux logo。GNOME“关于”图标已替换，备用 Plymouth 素材也已处理，但 U-Boot 早期画面尚未实屏确认，未刷写启动固件。详见 [系统标志审查](../BRANDING.md)。不能为了改图标就宣称固件启动时间已经测完或所有开机画面已经替换。
