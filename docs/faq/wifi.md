# 为什么显示两个 Wi-Fi

实测整理：2026-10-26。结论适用于当前 RTL8852BE 驱动和镜像。

## 现象：GNOME 有两项无线设备

这台机器只有一块 PCIe Realtek RTL8852BE 无线网卡。驱动同时创建了 `wlan0` 和 `p2p0` 两个逻辑接口，NetworkManager 把两者都列为 `wifi`，GNOME 因而显示两项。

| 对象 | 实测状态 | 含义 |
| --- | --- | --- |
| `wlan0` | connected | 当前连接路由器的接口 |
| `p2p0` | disconnected | 同一物理网卡上的第二个逻辑接口 |
| `p2p-dev-wlan0` / `p2p-dev-p2p0` | wifi-p2p、disconnected | P2P 管理对象，不是额外硬件 |
| 物理无线设备 | 两个接口均指向 `phy0`，PCI 设备路径相同 | 没有两块无线网卡 |

## 原因：驱动预留了 P2P 接口

实际驱动名为 `rtl8852be`，内核模块名为 `8852be`。本机参数读回为：

```text
ifname = wlan%d
if2name = p2p%d
rtw_sel_p2p_iface = 1
```

这些参数与实际的 `wlan0` / `p2p0` 命名一致，说明第二接口由驱动创建，并选作 P2P 使用。Wi-Fi Direct 用于设备之间直接连接；本机并没有建立这样的连接。它不是此前 GNOME 桌面优化脚本额外制造的第二块网卡。

Linux 支持在同一物理无线设备上创建多个虚拟接口，具体组合、共享信道及并发能力由硬件和驱动决定。参考 [Linux 无线虚拟接口说明](https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw/vif.html) 和 [P2P 概览](https://wireless.docs.kernel.org/en/latest/en/developers/p2p/overview.html)。不能仅凭接口存在就断言本机已经通过热点、投屏或并发连接测试。

## 检查：只读，不断开网络

在目标板执行，输出可能带网络名称或地址，分享前先脱敏：

```sh
nmcli -f DEVICE,TYPE,STATE device
readlink -f /sys/class/net/wlan0/phy80211
readlink -f /sys/class/net/p2p0/phy80211
readlink -f /sys/class/net/wlan0/device
readlink -f /sys/class/net/p2p0/device
cat /sys/module/8852be/parameters/ifname
cat /sys/module/8852be/parameters/if2name
cat /sys/module/8852be/parameters/rtw_sel_p2p_iface
```

前两条 phy 路径应指向同一个无线设备，device 路径也应相同。换驱动后模块参数可能不同；不存在这些路径时先确认实际硬件和驱动，不照抄修改配置。

## 需要关闭吗

当前 `p2p0` 没有连接，日常通过 `wlan0` 上网即可。此次检查没有修改网络配置。若将来需要简化 GNOME 显示，应先评估 P2P 用途，再考虑让 NetworkManager 忽略该逻辑接口，并准备有线回退；忽略接口与禁用物理网卡是不同操作。

## 验证范围

已核对 NetworkManager、sysfs 物理归属和模块参数；未测试 Wi-Fi Direct 对端连接、热点、投屏或并发吞吐。公开摘要见 [无线接口审查证据](../../board/evidence/20261026-wifi-interfaces.json)。
