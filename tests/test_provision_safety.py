# SPDX-License-Identifier: GPL-2.0-only
import io,json,os,socket,sys,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'board'))
from lib.browser import repair
from lib.provision import unpack_mesa,checked_file,change_password
class BrowserRecovery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)/'chromium';self.p.mkdir();(self.p/'Bookmarks').write_text('user-data')
  for k,v in {'SingletonLock':'oldhost-1234','SingletonCookie':'cookie','SingletonSocket':'/tmp/nonexistent-lbm5-test-socket'}.items():(self.p/k).symlink_to(v)
  self.running=patch('lib.browser.browser_running',return_value=False);self.running.start();self.addCleanup(self.running.stop)
  self.fs=patch('lib.browser.subprocess.check_output',return_value='ext4\n');self.fs.start();self.addCleanup(self.fs.stop)
 def test_stale_recovery_keeps_data_and_archives_only_links(self):
  r=repair(self.p,os.getuid(),apply=True);self.assertEqual(len(r['removed']),3);self.assertEqual((self.p/'Bookmarks').read_text(),'user-data');self.assertEqual(json.loads(Path(r['backup']).read_text())['SingletonLock'],'oldhost-1234')
  self.assertEqual(repair(self.p,os.getuid(),apply=True)['removed'],[])
 def test_live_browser_never_unlocks(self):
  with patch('lib.browser.browser_running',return_value=True):
   with self.assertRaisesRegex(RuntimeError,'running'):repair(self.p,os.getuid(),apply=True)
  self.assertTrue((self.p/'SingletonLock').is_symlink())
 def test_live_socket_never_unlocks(self):
  socketpath=Path('/tmp')/('lbm5-test-'+str(os.getpid()));s=socket.socket(socket.AF_UNIX);s.bind(str(socketpath));s.listen(1)
  self.addCleanup(s.close);self.addCleanup(socketpath.unlink);(self.p/'SingletonSocket').unlink();(self.p/'SingletonSocket').symlink_to(socketpath)
  with self.assertRaisesRegex(RuntimeError,'live'):repair(self.p,os.getuid(),apply=True)
 def test_shared_profile_and_nonlinks_are_rejected(self):
  with patch('lib.browser.subprocess.check_output',return_value='nfs4\n'):
   with self.assertRaisesRegex(RuntimeError,'filesystem'):repair(self.p,os.getuid(),apply=True)
  (self.p/'SingletonCookie').unlink();(self.p/'SingletonCookie').write_text('not a symlink')
  with self.assertRaisesRegex(RuntimeError,'non-symlink'):repair(self.p,os.getuid(),apply=True)
 def test_dry_run_and_wrong_host_leave_links(self):
  self.assertEqual(repair(self.p,os.getuid())['removed'],[])
  with self.assertRaisesRegex(RuntimeError,'previous host'):repair(self.p,os.getuid(),apply=True,previous_hostname='different')
  self.assertTrue((self.p/'SingletonLock').is_symlink())
class ArchiveSafety(unittest.TestCase):
 def test_path_traversal_and_escaping_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   for name,link in [('../outside',''),('mesa-26.2.3/lib','/etc')]:
    archive=Path(d)/'a.tar'
    with tarfile.open(archive,'w') as t:
     entry=tarfile.TarInfo(name)
     if link:entry.type=tarfile.SYMTYPE;entry.linkname=link;t.addfile(entry)
     else:entry.size=1;t.addfile(entry,io.BytesIO(b'x'))
    with self.assertRaises(RuntimeError):unpack_mesa(archive,Path(d)/'out')
   self.assertFalse((Path(d)/'outside').exists())
 def test_input_hash_must_match(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input';p.write_bytes(b'x')
   with self.assertRaisesRegex(RuntimeError,'checksum'):checked_file(p,'0'*64,'input')
class PasswordPAMFlow(unittest.TestCase):
 def test_three_secret_tokens_use_a_controlling_tty(self):
  with tempfile.TemporaryDirectory() as d:
   fake=Path(d)/'runuser'
   fake.write_text("#!/usr/bin/python3\nimport sys\nfor prompt,expected in [('Current password:','test-old'),('New password:','test-new-123'),('Retype new password:','test-new-123')]:\n print(prompt,flush=True)\n if sys.stdin.readline().strip()!=expected:sys.exit(3)\n")
   fake.chmod(0o755)
   with patch.dict(os.environ,{'PATH':d+':'+os.environ['PATH']}),patch('lib.provision.getpass.getpass',side_effect=['test-old','test-new-123','test-new-123']):
    self.assertEqual(change_password('fixture-user'),'test-new-123')
if __name__=='__main__':unittest.main()
