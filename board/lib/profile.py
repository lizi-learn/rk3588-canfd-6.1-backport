# SPDX-License-Identifier: GPL-2.0-only
"""Pure transformations for the narrow, tested carrier/BSP profile."""
import re
FD_OVERLAY='/dtb/overlay/rk3588-lbm5-canfd-overlay.dtbo'
def boot_config(text,fd=False,second=True):
 lines=text.splitlines();found=0
 enabled=['uart4-m2','can1-m1','can2-m0','5io-hdmi0-vp0']+(['uart7-m2'] if second else [])
 values={f'/dtb/overlay/rk3588-lubancat-{name}-overlay.dtbo':True for name in enabled}
 for name in ['5io-hdmi1-vp2','5io-rs485-1','5io-rs485-2']+([] if second else ['uart7-m2']):
  values[f'/dtb/overlay/rk3588-lubancat-{name}-overlay.dtbo']=False
 values[FD_OVERLAY]=fd;seen=set()
 for i,line in enumerate(lines):
  if line.startswith('bootargs='):
   found+=1
   args=[x for x in line.split('=',1)[1].split() if x not in ['splash','ignore_loglevel','quiet'] and not x.startswith(('loglevel=','plymouth.enable=','drm.edid_firmware=','video=HDMI-A-1:'))]
   lines[i]='bootargs='+' '.join(args+['quiet','loglevel=4','plymouth.enable=0','drm.edid_firmware=HDMI-A-1:edid/1920x1080.bin','video=HDMI-A-1:1920x1080@60e'])
  value=line.lstrip('#').strip()
  if value.startswith('dtoverlay='):
   name=value.split('=',1)[1]
   if name in values:
    if name in seen:lines[i]='';continue
    seen.add(name);lines[i]=('' if values[name] else '#')+value
 if found!=1:raise ValueError('Expected exactly one bootargs line in the active board file.')
 for name,on in values.items():
  if name not in seen and on:lines.append('dtoverlay='+name)
 return '\n'.join(lines).rstrip()+'\n'
def section(text,name,values):
 pattern=r'(?ms)^\['+re.escape(name)+r'\][ \t]*\n(.*?)(?=^\[|\Z)';m=re.search(pattern,text)
 if not m:return text.rstrip()+'\n\n['+name+']\n'+''.join(k+'='+v+'\n' for k,v in values.items())
 body=m.group(1)
 for k,v in values.items():
  body=re.sub(r'(?m)^\s*#?\s*'+re.escape(k)+r'\s*=.*\n?','',body);body+=k+'='+v+'\n'
 return text[:m.start(1)]+body+text[m.end(1):]
