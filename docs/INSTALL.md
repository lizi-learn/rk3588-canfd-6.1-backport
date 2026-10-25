> 历史驱动开发资料（v0.1.0）。本文件中的“外部未验证”指旧设备当时状态。新板外部 1M/5M、485 实测及最新位时序请见 [BOARD_KIT.md](BOARD_KIT.md) 和 `board/evidence/`。旧工具会改速率，不用于本次台架验收。

# 安装、启动与回退

## 1. 先核对目标

本例只针对 Linux 6.1.172 ARM64 与已验证的 RK3588 两路映射。
需要匹配的内核构建目录和符号版本；保留其他底板、内核、引脚与时钟配置。
先停止两路 CAN 业务。原 `rk3568_can` 是内置驱动时，不能靠黑名单模块将其移除。
本方案用设备树 compatible 在下一次启动时直接绑定新模块，不执行运行中热解绑。

## 2. 为本次安装新建备份

在仓库根目录运行以下 Bash 命令，保留输出的备份目录。
这只备份本项目涉及的文件，不复制其他设备配置。

```sh
canfd_backup="/var/backups/rk3588-canfd-$(date +%Y%m%d-%H%M%S)"
sudo mkdir -p "$canfd_backup"
for f in /boot/firmware/ubuntuEnv.txt \
 /lib/modules/6.1.172/extra/lbm5_canfd.ko \
 /etc/modules-load.d/lbm5-canfd.conf \
 /boot/firmware/dtb/overlay/rk3588-lbm5-canfd-overlay.dtbo
do
  if sudo test -e "$f"; then
    sudo cp -a --parents "$f" "$canfd_backup"
  else
    printf '%s\n' "$f" | sudo tee -a "$canfd_backup/absent-before.txt" >/dev/null
  fi
done
printf '%s\n' "$canfd_backup"
```

## 3. 编译并安装

依 README 先执行 `make`、`make overlay` 和 `make check`。
核对 `modinfo driver/lbm5_canfd.ko` 的 vermagic 与目标内核匹配。

```sh
sudo install -d /lib/modules/6.1.172/extra
sudo install -m 0644 driver/lbm5_canfd.ko /lib/modules/6.1.172/extra/
sudo install -m 0644 config/lbm5-canfd.conf /etc/modules-load.d/
sudo install -m 0644 build/rk3588-lbm5-canfd-overlay.dtbo \
  /boot/firmware/dtb/overlay/
sudo depmod -a 6.1.172
```

编辑 `/boot/firmware/ubuntuEnv.txt`，保留其余内容。已存在的原 CAN 引脚插件不重复添加；FD 插件放在其后：

```text
dtoverlay=/dtb/overlay/rk3588-lubancat-can1-m1-overlay.dtbo
dtoverlay=/dtb/overlay/rk3588-lubancat-can2-m0-overlay.dtbo
dtoverlay=/dtb/overlay/rk3588-lbm5-canfd-overlay.dtbo
```

示例 FD 插件指向 `/can@fea60000` 和 `/can@fea70000`，只改变 compatible 和 assigned-clock-rates。
目标节点路径、原引脚复用与时钟父级必须核对；不要照搬到其他型号。
保持原来的 UART、无屏显示、网络等配置，然后重启。

```sh
sudo reboot
```

## 4. 核对绑定与速率

```sh
readlink -f /sys/class/net/can0/device
readlink -f /sys/class/net/can1/device
readlink -f /sys/class/net/can0/device/driver
readlink -f /sys/class/net/can1/device/driver
ip -details -statistics link show can0
ip -details -statistics link show can1
```

设备应为 fea60000.can / fea70000.can，驱动路径末尾为 lbm5_canfd。
之后按 README 为两路设置速率。FD 模式应显示 MTU72、FD、仲裁 1000000、数据 5000000、时钟 300000000。
正常通信保持 LOOPBACK 关闭。ERROR-ACTIVE 是错误管理状态名，不表示当前一定出现错误。

接纯经典 CAN 总线时，先关闭 FD 并与对端匹配速率：

```sh
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000 fd off loopback off
sudo ip link set can0 up
```

对 can1 同样操作。修改网络参数不需整机重启；设备树和模块切换需重启。

## 5. 回退

使用刚才新建的备份目录，逐项恢复其中原来存在的文件；`absent-before.txt` 列出的目标为本次新增，核对后删除。
如安装后又修改过启动文件，先保存当前版本并合并处理，避免覆盖后续显示、串口或其他插件。
恢复完成后运行 `sudo depmod -a 6.1.172` 并重启，核对原驱动绑定与业务速率。
仅执行 rmmod 或恢复文件不代表已完成启动驱动切换。

该公共仓库不包含任何特定设备的历史备份，也不假称新设备已经安装或验证。
