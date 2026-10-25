# 系统标志与启动审查（v0.3.1）

使用官网原始大脑 PNG，SHA256 `c3fb34bb5b182375cbb30c5d9e2cc16808203e5b5b22a0781b7e1fbbaba635b6`。不改变 Ubuntu 操作系统身份或内核版本，不重画标志。

## 已有设备更新

新机 `setup` 已包含本步骤。已装 v0.3.0 的设备更新源码后只执行：

```sh
sudo ./board/brand.sh          # 查看资源和启动审查，不修改
sudo ./board/brand.sh --apply  # 替换已支持的全局标志
# 关闭后重新打开“设置 → 关于”，即可看到新图标
sudo ./board/verify.sh         # 独立只读检查，包含新图标哈希
```

固定启动器对应 `bash /tmp/rk3588-kit.sh brand --apply`。`brand` 不需要终止桌面、改名、改密码或重跑 CAN/485 配置。

| 位置 | 处理 / 验证 |
| --- | --- |
| GNOME 关于浅色图标 `/usr/share/pixmaps/ubuntu-logo-icon.png` | 已替换；重新打开设置并截图确认大脑标志 |
| GNOME 关于深色图标 `/usr/share/pixmaps/ubuntu-logo-dark.png` | 同一原始 PNG，核对哈希；未另行切换暗色主题验收 |
| Plymouth spinner 的 `watermark.png`、`bgrt-fallback.png` | 替换根文件系统备用资源，核对哈希；不是活动启动画面验收 |
| Linux 内核启动标志 | 配套 `/boot/config-6.1.172` 的 `CONFIG_LOGO` 未启用 |
| Plymouth 活动启动动画 | `/proc/cmdline` 为 `plymouth.enable=0`，没有 `splash`；继续保留快速启动设置 |
| 已构建的 initramfs | 未重建，里面的历史资源未声称替换；在当前禁用 Plymouth 的启动路径中不显示 |
| U-Boot 更早期画面 | 只读审查；没有实屏验收，不推断“绝不显示旧 logo”，不刷写引导程序 |

实机没有 `/boot/{logo.bmp,logo_kernel.bmp,resource.img}` 或 `/boot/firmware/` 下相应文件；GPT 只有 system-boot 和 writable 文件系统分区，没有独立 resource/logo 分区。U-Boot 前16MiB只读扫描发现 logo 文件名字符串，这是读取逻辑存在的证据，不能当作旧图片仍在显示或已替换的证据。本次运行日志的 `drm-logo@0` 预留大小为0，没有显示出已交接的 logo 帧缓冲区。

[厂商旧镜像说明](https://doc.embedfire.com/linux/rk356x/build_and_deploy/en/latest/building_image/building_kernel/kernel_logo.html) 提到直接替换 `/boot/logo.bmp`；本机使用独立 ext4 boot 分区、boot.scr/booti、不同目录布局，不能照搬并声称生效。审查还参考了 [LubanCat U-Boot 的资源读取实现](https://github.com/LubanCat/u-boot/blob/b14196eade471bbc000c368f8555f2a2a1ecc17d/arch/arm/mach-rockchip/resource_img.c)，但未证明其源码提交与这台自定义固件逐字对应。早期固件画面若以后需要定制，需匹配此固件构建/资源布局，并在接屏或启动串口下验证。

## 备份、升级与范围

使用本地 dpkg diversion 将四个原文件保留为 `.ymbot-vendor`，避免 gnome-control-center-data / Plymouth 软件包升级覆盖新图标。已有不相关 diversion 时拒绝覆盖。备份及结果位于 `/var/backups/rk3588-board-kit/时间戳/` 和 `/var/lib/rk3588-board-kit/last-branding.json`；初次执行、重复执行、实际回退并重新应用均已检查。

回退示例：

```sh
sudo ./board/rollback.sh /var/backups/rk3588-board-kit/首次改标备份 --dry-run
sudo ./board/rollback.sh /var/backups/rk3588-board-kit/首次改标备份
```

应选首次创建 diversion 的备份；后续重复执行快照用于恢复到其执行前的状态，不会撤销更早的 diversion。回退工具会核对原文件哈希、当前 diversion 目标，再删除本次创建的覆盖并恢复厂商文件。

实机完成图标替换、重复执行、实际回退与重应用、关于页面截图及健康检查；固件前缀、boot.scr、vmlinuz、initrd.img 和活动 uEnv 配置的前后 SHA256 一致。未重启、未做物理显示器的开机录像或电源上电到桌面秒表测试，不把文件检查写成开机画面实测。
