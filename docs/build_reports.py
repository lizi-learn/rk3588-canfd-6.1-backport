# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import json,hashlib,html,re
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Preformatted,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/pdf';REPO=ROOT;E=REPO/'board/evidence'
OUT.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('CJK','/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',subfontIndex=0))
INK=colors.HexColor('#19344b');TEAL=colors.HexColor('#087e8b');GRAY=colors.HexColor('#516171');LIGHT=colors.HexColor('#eef4f7');AMBER=colors.HexColor('#fff2da')
W,H=A4;WIDTH=W-96
style={
 'body':ParagraphStyle('body',fontName='CJK',fontSize=10,leading=16,textColor=INK,spaceAfter=8,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='CJK',fontSize=8.3,leading=12,textColor=GRAY,spaceAfter=6,wordWrap='CJK'),
 'title':ParagraphStyle('title',fontName='CJK',fontSize=21,leading=29,textColor=INK,spaceAfter=16),
 'sub':ParagraphStyle('sub',fontName='CJK',fontSize=12.5,leading=18,textColor=TEAL,spaceBefore=10,spaceAfter=9),
 'cell':ParagraphStyle('cell',fontName='CJK',fontSize=9,leading=13,textColor=INK,wordWrap='CJK'),
 'code':ParagraphStyle('code',fontName='CJK',fontSize=8.1,leading=12,textColor=INK,backColor=LIGHT,borderPadding=9,spaceAfter=10)
}
url='https://github.com/lizi-learn/rk3588-canfd-6.1-backport'
def load(name,default=None):
 p=E/name
 return json.loads(p.read_text()) if p.exists() else (default or {})
latest=load('20261025-kit-final.json');phy=latest.get('physical',{});boot=latest.get('boot_measurement','最终重启测量见随附 evidence JSON；历史复测为 7.151s。')
def p(t,kind='body'):return Paragraph(html.escape(str(t)).replace('\n','<br/>'),style[kind])
def table(rows,widths):
 data=[[p(v,'cell') for v in row] for row in rows]
 t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#d6e0e5'))]))
 return t
def code(s):
 lines=[]
 for line in s.strip('\n').splitlines():
  current=''
  for ch in line:
   if pdfmetrics.stringWidth(current+ch,'CJK',8.1)>WIDTH-22:
    lines.append(current);current='  '+ch
   else:current+=ch
  lines.append(current)
 return Preformatted('\n'.join(lines),style['code'])
def box(s):
 t=Table([[p(s)]],colWidths=[WIDTH]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),AMBER),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#dcaf59')),('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),3)]));return t

def build(name,title,pages):
 story=[]
 for i,(heading,items) in enumerate(pages):
  if i:story.append(PageBreak())
  story.append(p(heading,'title'))
  for item in items:story.append(p(item) if isinstance(item,str) else item)
 def footer(c,doc):
  c.setStrokeColor(colors.HexColor('#ced9df'));c.line(48,43,W-48,43);c.setFont('CJK',8);c.setFillColor(GRAY)
  c.drawString(48,29,'LBM5-DIBAN-V01A / lubancat-test / v0.2.0 / 2026-10-25')
  c.drawRightString(W-48,29,f'{doc.page}')
 doc=SimpleDocTemplate(str(OUT/name),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=57,title=title,author='LBM5 设备调试记录',subject='真实测量、通过/失败边界和可复现操作',pageCompression=1)
 doc.build(story,onFirstPage=footer,onLaterPages=footer)

can_delta=phy.get('can_error_delta',{})
can_desc='；'.join(n+': '+(', '.join(k+'='+str(v) for k,v in d.items() if v) or '所检错误增量0') for n,d in can_delta.items()) or '见最终 evidence JSON'
serial_desc=phy.get('rs485_turnaround',{})
report=[
('设备优化与真实验证报告',[
 p('RK3588 + LBM5-DIBAN-V01A · 新设备 lubancat-test','sub'),
 '记录日期：2026-10-25（Asia/Shanghai）。主对象是同款底板、两路 RS485 均已焊接的新设备；旧机内部回环记录只作为驱动开发历史，不能替代本台外部验收。',
 box('结论按最新复测更新：启动、无屏桌面配置已落实；RS485 具有真实对插记录。CAN 曾单次通过，但重复验证发现原厂驱动偶发丢失/重复、专用驱动勘误恢复，以及 5M FD 新增总线错误，不能宣称 CAN 已稳定零错误验收。'),
 table([['项目','真实结果 / 发布状态'],['启动','systemd 基线 60.614s → 优化后6.627s，随后7.151s，本次最终6.598s。无线就绪另计，约日志时间轴 23–24s。'],['GNOME / GPU','X11、无屏 1920×1080@60、Mali-G610 MC4 / Panfrost / Mesa 26.2.3，Accelerated=yes。'],['普通 CAN 1M','历史 24,002 帧零错误。封装复测原厂驱动有 1 帧缺失、1 帧重复；专用驱动数据完整但出现勘误6恢复计数。'],['CAN FD 1M/5M','历史 43,202 帧零错误；重启后同规模全部收到，却新增 bus_error 49/45，稳定性未通过。'],['两路 RS485','9600 / 115200、双向精确数据核对及200次换向；结果见第6页及最终 JSON。'],['远程桌面','NoMachine 认证和桌面流有记录；ToDesk 服务/固定密码/云连接有记录，完整对端交互未验收。']],[97,WIDTH-97]),
 '验收标准：不能只看收到了数据。必须同时检查逐帧/字节一致性、丢失/重复、控制器模式、对端硬件路径、错误增量和测试范围。脚本保留失败并返回非零。',
]),
('从接手到配置完成',[
 '1. 接手与网络：经有线中转登录设备，核对 RK3588、底板型号、Ubuntu 22.04.5 ARM64、内核 6.1.172（2026-10-17 构建）及两路485装配；配置目标 Wi-Fi 后，确认实际地址可从管理电脑 SSH 访问。公开材料移除网络口令、地址和远控身份。',
 '2. 建立基线：保存启动耗时、关键链、失败服务、显示/GPU、CAN/UART设备映射与原配置。基线存在 NetworkManager-wait-online 失败、Plymouth等待26.017s及空置HDMI探测延迟。',
 '3. 修改真实启动入口：确认 /boot/firmware/ubuntuEnv.txt 指向板型文件 /boot/firmware/uEnv/uEnv-lubancat-5io.txt。对所有启用插件先执行 fdtoverlay 合并，并检查 CAN/UART 节点 okay，避免只编辑未生效的备用文件。',
 '4. 接口配置：启用 UART4M2 / UART7M2、CAN1M1 / CAN2M0。MAX13488 使用自动方向，关闭原板 GPIO-DE 485 插件。建立别名、dialout 权限和 lbm5-can.service，默认普通 CAN 1M、485 115200/8N1。',
 '5. 无屏/应用：GNOME 固定 X11自动登录；内置1080p EDID与HDMI0强制输出、禁空置HDMI1；启用已有Mesa/Panfrost路径和DRI3，调整光标/翻页兼容选项。Chromium依会话选X11/Wayland并选ANGLE GLES；声音设置从完整GNOME环境启动。',
 '6. 远程/启动：保留NoMachine9.2.18，安装/配置ToDesk4.8.5.1并设置安全密码；按用户要求禁NoMachine音频转发。禁空闲休眠/锁屏；无远程文件系统时取消network-online阻塞，关闭Wi-Fi省电。保留原密钥环。',
 '7. 真实验证与固化：先健康检查，再在硬件同事完成对插后做实际双向收发。将过程整理为独立 optimize.sh、verify.sh 和 rollback.sh。复测暴露的问题保留在发布材料中，优化命令完成不等于验证通过。',
 p('当前工具是上述 BSP 的增量配置，不包含刷机、通用 Mesa 安装或商业远控授权。未在一张全空白系统镜像上完成全自动安装验收。','small')
]),
('启动、无屏桌面与应用',[
 table([['测量口径','基线 / 优化后'],['systemd-analyze time','24.795s kernel + 35.818s userspace = 60.614s；优化后 2.529s + 4.097s = 6.627s；随后 2.527s + 4.623s = 7.151s。'],['graphical.target','基线 userspace 35.789s；7.151s那次 userspace 4.597s。'],['日志就绪时刻','7.151s那次journal：GNOME 9.799s、Wi-Fi 23.189s；最终6.598s那次：GNOME 9.995s、Wi-Fi激活23.345s、CONNECTED_GLOBAL 23.856s。'],['本次封装最终重启',boot]],[112,WIDTH-112]),
 '以60.614s与6.627s比较，systemd指标缩短约89.1%；这是有限重启样本，未做统计分布。系统目标到达与远程可操作不同；未测电源上电、U-Boot、Wi-Fi关联和远控客户端连接的总秒表时间。此BSP早期printk时钟存在偏移，不能把不同时间轴直接混算。',
 '内置 EDID 已从内核日志确认：edid/1920x1080.bin 是内核内置预设，不要求磁盘上另有同名文件。只用于本次无实体显示器场景，不据此关闭所有显示控制器。',
 'GPU 证明：glxinfo -B 输出 Mali-G610 MC4 (Panfrost)、Mesa26.2.3、direct rendering Yes、Accelerated yes。llvmpipe 代表CPU软件绘制；此次最终GPU记录为硬件加速。图形加速不等于所有视频编解码路径均已验收。',
 'Chromium与声音面板：历史应用复测各存活15秒，Chromium出现X11 GPU进程；这是启动存活检查，未做长时间浏览、视频或全功能音频测试。声音面板的远程启动修复保留完整GNOME环境，包括XDG_CURRENT_DESKTOP。',
 'NoMachine：9.2.18-3，NX-password认证成功、display channel与H.264流建立；鼠标键盘未专项实测。音频转发明确禁用。ToDesk：4.8.5.1服务/GUI自启、云AuthOk和固定加密密码配置已查，对端固定密码登录与完整控制未做。',
]),
('普通 CAN 1M：复测与勘误',[
 table([['逻辑接口','控制器 / 引脚复用'],['CAN-A / can0','fea60000.can / CAN1M1；J46与J47是同一路并联。'],['CAN-B / can1','fea70000.can / CAN2M0；J50与J51是同一路并联。'],['最终默认','普通CAN 1Mbps，FD关闭、内部回环关闭。专用回移驱动 lbm5_canfd；300MHz，仲裁采样80%、SJW16。']],[112,WIDTH-112]),
 '历史实测：19:23:55–19:24:37，原厂rk3568_can双向每向10,000标准帧+2,000扩展帧+1烟测帧，共24,002帧，8字节载荷，目标2000帧/秒；当次丢失/重复/错帧及错误增量均为0。',
 '封装复测：20:32原厂驱动最后一组 can1→can0 的2000扩展帧中，唯一接收1999、重复1。不得沿用历史通过结果。驱动切换后完整24002帧收到，但20:41一轮can1 tx_errors增加19；ethtool的tx_extended_as_standard_errors也为19。',
 '源代码对应：回移驱动 rockchip_canfd-rx.c 的勘误6分支识别“扩展帧被发成标准帧”，增加上述专用统计和tx_errors并重试。这说明此次19次记录与该恢复路径一致；并不证明线束、电源和其他问题均已排除，也不能把恢复重试算成零错误。',
 '最终20:48:37–20:49:19封装复测：24,002帧数据完整；新增计数：'+can_desc+'。完整逐组结果与每轮状态以 board/evidence/20261025-kit-final.json 为准。',
 '验证排除假回环：两个控制器映射核对；CAN LOOPBACK关闭；CAN_RAW_LOOPBACK=0、RECV_OWN_MSGS=0；cangw规则为空；数据含随机nonce和递增序号，对端硬件接收逐帧核对。标准CAN过滤器未遍历全总线所有未知ID，因此还必须检查勘误/错误计数。',
 box('默认保留1M配置用于后续调试。当前有收发能力，但不能给出“所有CAN场景稳定合格”结论；扩展帧互操作仍需持续复核。'),
]),
('CAN FD 5M：成功与失败均留档',[
 '5M 指 FD+BRS 的数据阶段；仲裁仍1M。普通CAN帧不能以5M发送。500k是此前配置值，不是控制器上限；当前没有探明整机可靠最高速率。',
 table([['试验','结果 / 判定'],['默认自动位时序','1M/5M、数据BRP2、80%采样。43,202帧收到但bus_error增128/132：失败。'],['只调整SJW','短测曾零错误；完整43,202帧时bus_error增36/39：失败。'],['BRP10历史单轮','19:56:02–19:56:24，共43,202帧、4–64字节、标准/扩展FD+BRS，逐帧及SHA256一致，新增错误0：仅该轮通过。'],['BRP10重启复测','相同位时序、相同源码，全部43,202帧收到；bus_error新增49/45：稳定性未通过。'],['补充探测','BRP12（80%）12,000帧仍新增23/31总线错误；BRP20（66.7%）帧测试失败；BRP10短探测也新增24/27错误。']],[110,WIDTH-110]),
 'BRP10参数：clock300MHz；仲裁1M，采样80%，SJW16；数据5M，BRP10，6TQ/bit，prop=2、phase1=2、phase2=1，采样83.3%，SJW1。TQ理论33.333ns，ip显示整数33ns。保留上游RK3588 TDC=0处理。',
 '完整矩阵每方向：10,000标准64字节+10,000扩展64字节+1,600可变长度帧+1烟测帧，合计每向21,601帧。长度序列4/5/6/7/8/12/16/20/24/32/48/64；验收要求FD+BRS标志正确、无丢失重复、哈希一致且所有错误增量为0。',
 box('发布的 fd5m 入口属于实验复现，不能按稳定5M用于业务验收。下一步需记录实际线长、双绞与共地、终端电阻、实装收发器及供电，并用示波器检查波形；现有日志不足以把根因定为单一硬件或软件。'),
]),
('两路 RS485：真实对插验证',[
 table([['接口','已确认映射'],['RS48_1','UART4M2 / ttyS4 / feb70000.serial；别名 /dev/rs485_1、/dev/rs48_1。'],['RS48_2','UART7M2 / ttyS7 / feba0000.serial；别名 /dev/rs485_2、/dev/rs48_2。'],['电气与参数','两路MAX13488已焊接、自动方向；默认115200、8N1、无硬件流控。GPIO方向插件关闭。']],[100,WIDTH-100]),
 table([['测试项','数据量 / 判定'],['双向烟测','每向32字节。'],['9600/8N1','每向4096字节，逐字节与SHA256核对。'],['115200/8N1','每向65,536字节，逐字节与SHA256核对。'],['半双工换向','200次交替事务，包长1/2/7/31/64/255字节，共11,883字节。'],['错误检查','UART MCR内部回环位关闭；TIOCGICOUNT的frame/parity/overrun/buf_overrun等增量应为0；结束恢复原termios。'],['最终复测','完成换向 '+str(serial_desc.get('completed_turns','见最终JSON'))+' 次；六组双向烟测/批量、200次换向全部通过，frame/parity/overrun等增量均0。20:48:37–20:49:19。']],[100,WIDTH-100]),
 '历史19:24与最终20:49两轮全部通过，发送端观察到物理自回显。成功统计以另一路UART接收为准，不把发送端回显当成对端响应；业务协议需剔除本机回显并留足半双工换向时间。',
 '连接口径：J52/J53/J54均属于第一路并联，并非三路独立485。第二路RS485_2_A/B按实装引出点对插；图纸第17页J71 A3/A2经R458/R457连接，标为NC，需核对实装。该Type-C定义不是标准USB串口口。',
 '本报告只证明所记测试速率和本次对插。未测试RS485极限波特率、长线负载、多节点偏置、隔离、浪涌或EMC；没有终端/波形实测数据，不宣称工业现场合格。',
]),
('交付物、证据与未完成项',[
 '仓库：'+url+'（v0.2.0，实验发布）。优化入口board/optimize.sh；独立验收board/verify.sh；回退board/rollback.sh。固定版本bootstrap提供optimize/verify分开调用。',
 '来源：Linux上游固定提交5b0764a53235d3c77e1ed674e836e1b3fe1a4b1f；项目在6.1内核回移API并完成板级适配，不是从零自研整套CAN驱动。原版权、引用和GPL-2.0-only随仓库保留。',
 '编译与回退：目标机使用与运行内核匹配的厂商headers/config/Module.symvers，现场编译并通过modpost，不强制vermagic；全插件合并通过后才写入活动启动文件。重启绑定验证，避免热解绑控制器。备份包含文件哈希、服务与偏好，可按操作手册回退；软件包保留。',
 '证据索引：公开board/evidence包含历史1M/485、FD自动参数失败、SJW失败、BRP10单次通过、BRP10重复失败、原厂1M重复失败、专用驱动勘误统计及最终封装复测。每份摘要按白名单脱敏；原始日志本地留存，摘要提供SHA256用于核对。',
 '脚本质量：Python语法、5项启动配置保留/重复执行离线检查和shell语法检查；目标机已执行优化、重复配置、重启和真实总线验证。离线CI通过只能证明源码检查，不代表硬件绿灯。缺少软件的安装分支、完整回退恢复和远控全交互均不以本次预装设备复测代替。',
 box('待完成：CAN扩展帧勘误的互操作验证；5M错误根因和重复零错误验收；真实线束/接地/终端与波形记录；ToDesk对端认证和键鼠全交互；上电至可操作秒表测试；多板/长时/温度/EMC验证。'),
 p('参考：上游驱动及来源见仓库PROVENANCE.json、reference/upstream-driver/；NoMachine当前许可见 https://www.nomachine.com/support/faq 。图纸依据为用户提供的LBM5-DIBAN-V01A原理图与丝印图，原件不公开分发。本报告是软件配置与有限台架验证记录，不是整板安全审查或生产放行书。','small'),
])]

manual=[
('精简操作手册',[
 p('优化与验证分开 · v0.2.0','sub'),
 box('先确认适用镜像与底板。CAN存在已知复测异常，fd5m仅作实验；脚本会如实给失败，不默认绿灯。'),
 '适用：LBM5-DIBAN-V01A、RK3588、Ubuntu22.04 ARM64、LubanCat-5IOB BSP、Linux6.1.172。需要已有GNOME/GDM、/opt/mesa-26.2.3及完全匹配的厂商内核头文件。两路485均已焊接；备用未焊接板需--rs485-2 off。',
 'NoMachine预装9.2.18则保留；缺失时提供厂商ARM64服务端.deb和适用许可，优化命令加--nomachine-deb /绝对路径/安装包.deb。ToDesk已安装则保留版本与密码，缺失时使用清单中锁定哈希的社区包。新安装的固定密码需在ToDesk安全设置中建立；不把别机凭据写入仓库。',
 p('1  取固定版本并确认设备','sub'),
 code('git clone --branch v0.2.0 https://github.com/lizi-learn/rk3588-canfd-6.1-backport.git\ncd rk3588-canfd-6.1-backport\npython3 scripts/check_source.py\nuname -r\nsudo ./board/optimize.sh --carrier lbm5-diban-v01a --dry-run'),
 '脚本检查板型、ARM64、Ubuntu版本、活动U-Boot入口、Mesa和内核头文件；不支持的环境会停止。默认用户cat；其他用户加--user 用户名，验证也同样指定。',
 p('2  配无线网（有线SSH下可执行）','sub'),
 code('sudo ./board/wifi.sh\nnmcli -g IP4.ADDRESS device show wlan0'),
 '按提示输入SSID和密码，从管理电脑确认新地址能SSH访问。Wi-Fi配置与优化分开；不要把网络口令粘进命令参数或公开日志。',
]),
('一键优化与独立验证',[
 p('3  默认优化：普通CAN 1M + 两路485','sub'),
 code('sudo ./board/optimize.sh --carrier lbm5-diban-v01a\nsudo reboot'),
 '停止总线业务后运行。工具会本机构建专用CAN回移驱动，配置两路1M、485 115200/8N1、无屏1080p、GNOME X11自动登录、已有GPU栈、Chromium后端、远控自启、禁NoMachine音频、禁休眠/锁屏和启动等待优化。它不发送测试帧，不自动重启。',
 p('4  重连后独立检查','sub'),
 code('cd rk3588-canfd-6.1-backport\nsudo ./board/verify.sh\n# 仅接线核对完、隔离业务后执行下一条\nsudo ./board/verify.sh --physical'),
 '第一条只检查服务/速率/别名/显示/GPU等；--physical才做实际CAN和485收发。完整台架测试约一分钟，耗时随异常超时变化。RS485测试临时切波特率，结束恢复原值。',
 'JSON结果与时间戳在/var/lib/rk3588-board-kit/，默认root可读。读取退出码：echo $?；0仅表示本次所列检查通过，非0查看exception、failure_reason和每项计数。数据完整但错误增量不为0也判失败。',
 code('sudo cat /var/lib/rk3588-board-kit/last-optimize.json\nsudo /usr/local/sbin/lbm5-interfaces status\nip -details -statistics link show can0\nip -details -statistics link show can1'),
 '物理测试发生异常而抛出错误时会将CAN置down以停止重发；排除故障后 sudo systemctl restart lbm5-can.service，再验证。不要用清零计数代替修复。',
]),
('对插接线与验收标准',[
 table([['项目','接线 / 保护电源脚'],['CAN-A↔CAN-B','J46/J47任选一口 ↔ J50/J51任选一口；1↔1 CANH、2↔2 CANL、3↔3 GND。4脚24V不接。'],['RS48_1↔RS48_2','A↔A、B↔B、GND↔GND。J52/J53/J54均为第一路：2=A、3=B、4=GND，1脚5V不接。'],['第二路引出','UART7 / RS485_2_A/B：由硬件同事确认实装引出点。J71 A3/A2的NC电阻路由需核实，禁止按标准USB接口使用。']],[99,WIDTH-99]),
 '断电接线，复核丝印与针号方向，再上电。CAN若两端各120Ω，断电H-L约60Ω；按实装测量，不盲目加终端。记录线长、双绞、共地、终端与供电；本次历史测试没有这些仪器测量记录。',
 table([['验证','最低判定条件'],['普通CAN1M','双向24002帧：标准/扩展；无丢失/重复/错载荷；正常模式、无软件本地回显；总线和勘误/收发错误增量均0。'],['两路RS485','双向9600各4096字节、115200各65536字节、200次换向；精确匹配/哈希一致，串口错误增量0；MCR内部回环关闭。'],['5M FD实验','双向43202帧，4–64字节、标准/扩展FD+BRS；逐帧和哈希一致，所有错误增量0。当前复测未达到此标准。'],['远控','另用客户端验证登录、桌面显示和鼠标键盘；健康脚本不会自动证明完整对端控制。']],[99,WIDTH-99]),
 '485发送端物理自回显需要在业务层处理，只有另一UART的接收才算跨口成功。不要把J52与J53相接当成两个独立485通道。',
]),
('5M实验、回退与一键启动器',[
 p('5  实验性FD配置（当前稳定性未通过）','sub'),
 code('sudo ./board/optimize.sh --carrier lbm5-diban-v01a --can-mode fd5m\nsudo reboot\n# 重连后进入仓库目录\nsudo ./board/verify.sh --physical'),
 '仲裁1M / 数据5M；BRP10数据采样83.3%、SJW1，仲裁SJW16、clock300MHz、TDC=0。历史单次零错误，后续重启复测新增bus_error49/45，不能按稳定5M部署。先核查真实硬件条件与波形。',
 '恢复普通1M：执行第2页默认优化命令、重启并独立验证；继续使用专用驱动，FD模式关闭。原厂与回移驱动的已知复测异常均见详细报告，不能认为切换模式就消除了问题。',
 p('6  配置备份回退','sub'),
 code('sudo ./board/rollback.sh /var/backups/rk3588-board-kit/实际时间戳 --dry-run\nsudo ./board/rollback.sh /var/backups/rk3588-board-kit/实际时间戳\nsudo reboot'),
 '使用优化输出的真实备份路径，先核对dry-run。回退配置/服务开机状态/记录的偏好与Wi-Fi省电；保留安装的软件包。备份可能含私密应用配置，勿上传公开仓库。完整恢复分支未在空白新镜像上验收。',
 p('7  固定版本一键入口（替代手动git下载）','sub'),
 code('curl -fsSL https://raw.githubusercontent.com/lizi-learn/rk3588-canfd-6.1-backport/v0.2.0/board/bootstrap.sh -o /tmp/rk3588-kit.sh\nbash /tmp/rk3588-kit.sh optimize --carrier lbm5-diban-v01a\n# 手动重启并重连后，单独验证\nbash /tmp/rk3588-kit.sh verify --physical'),
 p('启动器下载固定版本release包并核对SHA256，优化与验证不会互相调用。源码、脱敏证据及本报告见 '+url+' 。','small'),
])]
build('lubancat-test-优化与真实验证报告.pdf','lubancat-test 优化与真实验证报告',report)
build('lubancat-test-精简操作手册.pdf','lubancat-test 精简操作手册',manual)
for f in OUT.glob('lubancat-test-*.pdf'):print(f)
