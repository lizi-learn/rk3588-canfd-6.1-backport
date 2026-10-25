#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
"""Independent verification. --physical sends traffic on an isolated, cross-wired bench."""
import argparse,configparser,fcntl,json,os,platform,re,sys,termios,time
from pathlib import Path
from lib.common import BOARD,STATE,configuration,now,profile,require,require_root,run,save_json,sha
PORTS={'can0':'fea60000.can','can1':'fea70000.can'}

def ethtool_stats(n):return {k:int(v) for k,v in re.findall(r'^\s+(\w+): (\d+)$',run('ethtool','-S',n),re.M)}
def can_info(n):return json.loads(run('ip','-j','-details','-statistics','link','show',n))[0]
def counter_delta(before,after):
 out={}
 for n,b in before.items():
  a=after[n];d={k:a['linkinfo']['info_xstats'].get(k,0)-v for k,v in b['linkinfo']['info_xstats'].items()}
  for way in ['rx','tx']:
   for k in ['errors','dropped','over_errors']:
    if k in a['stats64'][way]:d[way+'_'+k]=a['stats64'][way][k]-b['stats64'][way].get(k,0)
  out[n]=d
 return out

def check_can(before):
 is_fd=[]
 for n,device in PORTS.items():
  i=before[n];d=i['linkinfo']['info_data'];require(i['parentdev']==device,'CAN mapping differs: '+n)
  require('UP' in i['flags'] and d['state']=='ERROR-ACTIVE','CAN is not ready: '+n)
  modes=d.get('ctrlmode',[]);require(not any(x in modes for x in ['LOOPBACK','LISTEN-ONLY']),'CAN must be in normal mode.')
  require(d['bittiming']['bitrate']==1000000,'Expected nominal 1 Mbps.')
  require(d['berr_counter']=={'rx':0,'tx':0},'CAN error counters are nonzero before testing.')
  require(Path('/sys/class/net',n,'device/driver').resolve().name=='lbm5_canfd' and d['clock']==300000000 and d['bittiming']['sjw']==16,'Board kit requires the RK3588 backport in both classic and FD modes.')
  fd='FD' in modes;is_fd.append(fd)
  if fd:
   bt=d['data_bittiming'];segments=1+bt['prop_seg']+bt['phase_seg1']+bt['phase_seg2']
   brp=d['clock']//(bt['bitrate']*segments)
   require(Path('/sys/class/net',n,'device/driver').resolve().name=='lbm5_canfd','Expected backported FD driver.')
   require(d['clock']==300000000 and bt['bitrate']==5000000 and brp==10 and bt['sjw']==1 and abs(bt['sample_point']-5/6)<0.002 and d['bittiming']['sjw']==16,'FD timing is not the experimental reproduced 1M/5M BRP10 profile.')
 require(len(set(is_fd))==1,'CAN modes differ between ports.')
 return is_fd[0]

def physical(before,is_fd,rs485_on,r):
 from lib import bus_test as b
 from lib import fd_test as f
 import serial
 require(rs485_on,'Full two-channel cross-port test requires RS485_2_ENABLED=1.')
 for dev,hw in [('ttyS4','feb70000.serial'),('ttyS7','feba0000.serial')]:
  require(hw in Path('/sys/class/tty',dev,'device').resolve().parts,'UART mapping differs: '+dev)
 # can-utils cangw LIST returns sendto() byte count (36) on this BSP.
 # https://github.com/linux-can/can-utils/blob/master/cangw.c (main LIST path)
 gw=run('cangw','-L',check=False)
 require(gw.returncode in [0,36] and not gw.stdout.strip() and not gw.stderr.strip(),'CAN gateway query failed or rules are present; refusing a physical claim.')
 r.update({'started_at':now(),'can':[],'rs485':[],'uart_modes':b.modes(),'serial_counters_before':b.serial_counters(),'can_before':before,'ethtool_before':{n:ethtool_stats(n) for n in PORTS},'gateway_query':{'returncode':gw.returncode,'rules':[]}})
 require(all(not x['internal_loopback'] for x in r['uart_modes'].values()),'UART internal loopback is enabled.')
 for tx,rx,id_ in [('can0','can1',0x5a1),('can1','can0',0x5a2)]:
  case=f.transfer(tx,rx,1,100) if is_fd else b.can_direction(tx,rx,1,id_,100)
  r['can'].append(case);require(case['pass'],'CAN physical smoke failed; check wiring and termination.')
 groups=[(10000,False,(64,)),(10000,True,(64,)),(1600,False,(4,5,6,7,8,12,16,20,24,32,48,64))] if is_fd else [(10000,False,None),(2000,True,None)]
 for count,ext,lengths in groups:
  for tx,rx,id_ in [('can0','can1',0x5a1),('can1','can0',0x5a2)]:
   case=f.transfer(tx,rx,count,2000,ext,lengths) if is_fd else b.can_direction(tx,rx,count,0x80000000|0x1ce00000|id_ if ext else id_,2000)
   r['can'].append(case);require(case['pass'],'CAN cross-port frame comparison failed.')
 r['can_after']={n:can_info(n) for n in PORTS};r['can_error_delta']=counter_delta(before,r['can_after'])
 r['can_data_integrity_pass']=all(c['pass'] for c in r['can'])
 r['can_zero_error_pass']=all(v==0 for d in r['can_error_delta'].values() for v in d.values()) and all(i['linkinfo']['info_data']['berr_counter']=={'tx':0,'rx':0} for i in r['can_after'].values())
 r['ethtool_after']={n:ethtool_stats(n) for n in PORTS}
 r['ethtool_delta']={n:{k:v-r['ethtool_before'][n][k] for k,v in d.items()} for n,d in r['ethtool_after'].items()}
 r['can_zero_error_pass']=r['can_zero_error_pass'] and all(v==0 for d in r['ethtool_delta'].values() for v in d.values())
 original={};ports=[]
 try:
  for dev in ['/dev/ttyS4','/dev/ttyS7']:
   fd=os.open(dev,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
   try:original[dev]=termios.tcgetattr(fd)
   finally:os.close(fd)
  for dev in original:ports.append(serial.Serial(dev,115200,timeout=0,write_timeout=2,exclusive=True))
  for baud,total,block in [(115200,32,32),(9600,4096,256),(115200,65536,256)]:
   for port in ports:port.baudrate=baud;port.reset_input_buffer()
   for tx,rx in [ports,ports[::-1]]:
    case=b.serial_direction(tx,rx,total,block);r['rs485'].append(case);require(case['pass'],'RS485 cross-port byte comparison failed.')
  turns=[]
  for turn in range(200):
   tx,rx=ports if turn%2==0 else ports[::-1]
   case=b.serial_direction(tx,rx,[1,2,7,31,64,255][turn%6],256);turns.append(case);require(case['pass'],'RS485 half-duplex turnaround failed.')
  r['rs485_turnaround']={'requested_turns':200,'completed_turns':len(turns),'total_bytes':sum(c['received_bytes'] for c in turns),'pass':all(c['pass'] for c in turns)}
 finally:
  for port in ports:port.close()
  for dev,attrs in original.items():
   fd=os.open(dev,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
   try:termios.tcsetattr(fd,termios.TCSANOW,attrs)
   finally:os.close(fd)
 r['uart_modes_after']=b.modes();r['serial_counters_after']=b.serial_counters()
 r['serial_error_delta']={n:{k:r['serial_counters_after'][n][k]-v for k,v in d.items() if k in ['frame','overrun','parity','break','buf_overrun']} for n,d in r['serial_counters_before'].items()}
 require(all(not x['internal_loopback'] for x in r['uart_modes_after'].values()),'UART internal loopback changed.')
 require(all(v==0 for d in r['serial_error_delta'].values() for v in d.values()),'UART error counters increased.')
 r['ended_at']=now();r['pass']=r['can_zero_error_pass'] and len(r['can'])==(8 if is_fd else 6) and len(r['rs485'])==6 and r['rs485_turnaround']['completed_turns']==200
 return r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--physical',action='store_true',help='Send CAN and RS485 data on a correctly cross-wired, isolated bench; stop business applications first.')
 p.add_argument('--user',default='cat');p.add_argument('--output',type=Path);a=p.parse_args();require_root()
 lock=open('/run/lbm5-interface-test.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 out=a.output or STATE/('verification-'+now().replace(':','')+'.json')
 r={'started_at':now(),'kit_version':'0.2.0','scope':'health + physical cross-port tests' if a.physical else 'read-only health checks','hardware':{},'checks':{},'physical':'not requested','remote_peer_interaction':'not tested by this script','power_on_stopwatch':'not measured','pass':False}
 def check(name,ok,detail):r['checks'][name]={'pass':bool(ok),'detail':detail}
 try:
  device=profile();r['hardware']={'model':device['model'],'kernel_release':platform.release(),'kernel_build':platform.version(),'architecture':platform.machine()}
  before={n:can_info(n) for n in PORTS};is_fd=check_can(before);r['can_mode']='fd5m' if is_fd else 'classic1m'
  check('CAN normal mode and timing',True,{n:i['linkinfo']['info_data'] for n,i in before.items()})
  config=configuration();second=config.get('RS485_2_ENABLED','1')=='1'
  aliases={n:str(Path('/dev',n).resolve()) for n in ['rs485_1']+(['rs485_2'] if second else [])}
  check('RS485 aliases',aliases.get('rs485_1')=='/dev/ttyS4' and (not second or aliases.get('rs485_2')=='/dev/ttyS7'),aliases)
  for n in ['ttyS4']+(['ttyS7'] if second else []):
   status=run('stty','-F','/dev/'+n,'-a');check(n+' 115200 8N1',all(x in status for x in ['speed 115200 baud','cs8','-parenb','-cstopb','-crtscts']),status)
  for unit in ['gdm3.service','lbm5-can.service','nxserver.service','todeskd.service']:
   active=run('systemctl','is-active',unit,check=False).stdout.strip();check(unit,active=='active',active)
  r['boot_measurement']=run('systemd-analyze','time').strip()
  failed=json.loads(run('systemctl','--failed','--no-legend','--output=json'));check('systemd failed units',not failed,[x['unit'] for x in failed])
  session=BOARD/'assets/session-run.py'
  typ=run('python3',session,'--user',a.user,'printenv','XDG_SESSION_TYPE').strip();check('GNOME X11',typ=='x11',typ)
  gpu=run('python3',session,'--user',a.user,'glxinfo','-B');check('GPU accelerated', 'Accelerated: yes' in gpu and 'Mali-G610' in gpu and 'llvmpipe' not in gpu,gpu)
  display=run('python3',session,'--user',a.user,'xrandr','--current');check('headless 1080p', '1920x1080' in display and bool(re.search(r'current 1920\s*x\s*1080',display.splitlines()[0])), '\n'.join(x for x in display.splitlines() if '1920x1080' in x or ' connected' in x))
  nx=Path('/usr/NX/etc/node.cfg').read_text();check('NoMachine audio disabled',any(l.strip()=='EnableAudio 0' for l in nx.splitlines()) and any(l.strip()=='AudioInterface disabled' for l in nx.splitlines()),'EnableAudio=0, AudioInterface=disabled')
  c=configparser.ConfigParser(interpolation=None);c.read('/opt/todesk/config/config.ini');fixed=bool(c.get('configinfo','authpassex',fallback=''));check('ToDesk fixed password present',fixed,'Encrypted credential present; password authentication by a peer is outside this check.')
  if a.physical:
   print('Physical testing: CAN normal mode, no socket echo; UART baud rates restored after testing.',flush=True)
   # Save every completed subtest immediately, including when a later case fails.
   r['physical']={};physical(before,is_fd,second,r['physical'])
  r['pass']=all(x['pass'] for x in r['checks'].values()) and (not a.physical or r['physical']['pass'])
  if a.physical and not r['physical']['pass']:r['failure_reason']='Physical acceptance failed; inspect CAN counter deltas and subtest results.'
 except Exception as e:
  r['exception']=str(e)
  if a.physical:
   # Stop unacknowledged retransmissions on a failed bench. Do not silently retune.
   for n in PORTS:run('ip','link','set',n,'down',check=False)
 finally:
  r['ended_at']=now();save_json(out,r);print(json.dumps({'pass':r['pass'],'scope':r['scope'],'result_file':str(out),'failed_checks':[n for n,c in r['checks'].items() if not c['pass']],'physical_pass':r['physical'].get('pass') if isinstance(r['physical'],dict) else None,'exception':r.get('exception'),'failure_reason':r.get('failure_reason')},ensure_ascii=False,indent=2))
 return 0 if r['pass'] else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
