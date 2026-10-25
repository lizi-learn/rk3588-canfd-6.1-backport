# SPDX-License-Identifier: GPL-2.0-only
"""Version-specific ToDesk 4.8.5.1 local configuration; not vendor API."""
import configparser,hashlib,hmac,os,subprocess,time
from pathlib import Path
from .common import run,require

def encode(password):
 from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_encrypt,crypto_aead_xchacha20poly1305_ietf_decrypt
 require(8<=len(password)<=16 and password.isascii() and all(c.isalnum() for c in password),'ToDesk password: 8–16 ASCII letters/digits.')
 # Application format constants, not a device/account credential. Never decode existing passwords.
 source=b'www.todesk.com_D2FFB1DD591BB30CD2FFB1DD591BB30C';d=hashlib.md5(source).digest();master=d+hashlib.md5(d+source).digest()
 while True:
  salt=os.urandom(32);prk=hmac.new(salt,master,hashlib.sha1).digest();a=hmac.new(prk,b'ss-subkey\x01',hashlib.sha1).digest();b=hmac.new(prk,a+b'ss-subkey\x02',hashlib.sha1).digest();key=(a+b)[:32]
  ciphertext=crypto_aead_xchacha20poly1305_ietf_encrypt(password.encode(),b'',bytes(24),key);raw=salt+ciphertext
  if b'\0' not in raw:break
 require(crypto_aead_xchacha20poly1305_ietf_decrypt(ciphertext,b'',bytes(24),key)==password.encode(),'New credential self-check failed.')
 return raw.hex().upper()

def apply(encoded,user,snap):
 import pwd
 require(run('dpkg-query','-W','-f=${Version}','todesk').strip()=='4.8.5.1','Password writer supports only the tested ToDesk 4.8.5.1 package.')
 # Validate new payload without reading/decrypting existing credentials.
 raw=bytes.fromhex(encoded);require(56<=len(raw)<=64 and b'\0' not in raw,'Invalid new encrypted payload.')
 cfg=Path('/opt/todesk/config/config.ini');require(cfg.is_file(),'ToDesk has not created config.ini yet.')
 run('pkill','-TERM','-u',user,'-x','ToDesk',check=False);run('systemctl','stop','todeskd.service');time.sleep(1)
 try:
  if run('pgrep','-u',user,'-x','ToDesk',check=False).returncode==0:
   run('pkill','-KILL','-u',user,'-x','ToDesk',check=False);time.sleep(.3)
  c=configparser.ConfigParser(interpolation=None);c.read(cfg);require(c.has_section('configinfo'),'Unexpected ToDesk configuration.')
  identity=c.get('configinfo','clientid',fallback='');require(bool(identity),'ToDesk device identity is not initialized.')
  snap.remember(cfg)
  for k in ('authpass','authpassex'):c.remove_option('configinfo',k)
  for k,v in {'authpassex':encoded,'authmode':'1','isopentemppass':'0'}.items():c.set('configinfo',k,v)
  import io
  out=io.StringIO();c.write(out);snap.write(cfg,out.getvalue(),0o660);os.chown(cfg,0,pwd.getpwnam(user).pw_gid)
 finally:run('systemctl','start','todeskd.service')
 time.sleep(2);check=configparser.ConfigParser(interpolation=None);check.read(cfg)
 require(check.get('configinfo','clientid')==identity,'ToDesk identity unexpectedly changed.')
 require(check.get('configinfo','authpassex')==encoded and check.get('configinfo','authmode')=='1' and check.get('configinfo','isopentemppass')=='0','ToDesk credential readback mismatch.')
 require(run('systemctl','is-active','todeskd.service').strip()=='active','ToDesk service failed.')
 return {'fixed_password_updated':True,'new_payload_self_check':True,'configuration_readback_match':True,'device_identity_preserved':True,'temporary_password_enabled':False,'peer_password_login':'not tested'}
