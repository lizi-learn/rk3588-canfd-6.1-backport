# SPDX-License-Identifier: GPL-2.0-only
"""Offline checks for boot safety and repeatability; never claims hardware coverage."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'board'))
from lib.profile import boot_config,section,FD_OVERLAY
class BootProfile(unittest.TestCase):
 def setUp(self):
  self.original='bootargs=rootwait rw splash ignore_loglevel console=ttyS2,1500000\nfdtfile=rk3588-lubancat-5io.dtb\ndtoverlay=/dtb/overlay/keep-camera.dtbo\ndtoverlay=/dtb/overlay/rk3588-lubancat-5io-rs485-1-overlay.dtbo\n'
 def test_preserves_unrelated_boot_hardware(self):
  x=boot_config(self.original)
  self.assertIn('rootwait rw console=ttyS2,1500000',x);self.assertIn('dtoverlay=/dtb/overlay/keep-camera.dtbo\n',x)
  self.assertIn('#dtoverlay=/dtb/overlay/rk3588-lubancat-5io-rs485-1-overlay.dtbo',x)
 def test_switches_fd_without_duplicate_overlay(self):
  x=boot_config(self.original,True);self.assertEqual(boot_config(x,True),x)
  y=boot_config(x,False);self.assertEqual(boot_config(y,False),y)
  self.assertNotIn('\ndtoverlay='+FD_OVERLAY,y)
  self.assertEqual(sum(l=='dtoverlay='+FD_OVERLAY for l in x.splitlines()),1)
 def test_spare_uart_stays_disabled(self):
  x=boot_config(self.original,second=False)
  self.assertNotIn('\ndtoverlay=/dtb/overlay/rk3588-lubancat-uart7-m2-overlay.dtbo',x)
 def test_rejects_ambiguous_bootargs(self):
  for text in ['',self.original+'bootargs=other\n']:
   with self.assertRaises(ValueError):boot_config(text)
 def test_gdm_update_is_repeatable(self):
  x=section('[daemon]\n#WaylandEnable=true\n[security]\nOther=keep\n','daemon',{'WaylandEnable':'false','AutomaticLogin':'cat'})
  self.assertEqual(section(x,'daemon',{'WaylandEnable':'false','AutomaticLogin':'cat'}),x)
  self.assertIn('Other=keep',x)
if __name__=='__main__':unittest.main()
