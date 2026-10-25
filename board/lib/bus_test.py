# SPDX-License-Identifier: GPL-2.0-only
"""Physical CAN/UART transfers; never enables internal or socket loopback."""
import argparse, array, datetime, fcntl, hashlib, json, mmap, os, platform, select, socket, struct, subprocess, sys, termios, threading, time
from pathlib import Path
import serial

def run(*args):
    return subprocess.check_output(args,text=True)
def can_info(name): return json.loads(run('ip','-j','-details','-statistics','link','show',name))[0]
def modes():
    result={}; f=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
    try:
        for dev,addr in [('ttyS4',0xfeb70000),('ttyS7',0xfeba0000)]:
            with mmap.mmap(f,4096,mmap.MAP_SHARED,mmap.PROT_READ,offset=addr) as m:
                mcr=struct.unpack_from('<I',m,16)[0]
            result[dev]={'mcr':hex(mcr),'internal_loopback':bool(mcr&16)}
    finally: os.close(f)
    return result

def serial_counters():
    out={}
    for dev in ['/dev/ttyS4','/dev/ttyS7']:
        fd=os.open(dev,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            counters=array.array('i',[0]*20)
            fcntl.ioctl(fd,0x545d,counters,True)
            out[dev]=dict(zip(['cts','dsr','rng','dcd','rx','tx','frame','overrun','parity','break','buf_overrun'],counters))
        finally:os.close(fd)
    return out

def cansock(name,rxid):
    s=socket.socket(socket.PF_CAN,socket.SOCK_RAW,socket.CAN_RAW)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024*1024)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_LOOPBACK,0)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_RECV_OWN_MSGS,0)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_FILTER,struct.pack('=II',rxid,0xdfffffff))
    s.bind((name,)); s.setblocking(False)
    return s

def drain(s):
    while True:
        try: s.recv(16)
        except BlockingIOError: break

def can_direction(txname,rxname,count,canid,pps):
    nonce=os.urandom(4); tx=cansock(txname,0x7fe); rx=cansock(rxname,canid)
    seen=set(); unexpected=duplicates=0; recv_exception=None; send_exception=None
    done=threading.Event(); lock=threading.Lock(); start=time.monotonic()
    def receive():
        nonlocal unexpected,duplicates,recv_exception
        deadline=start+count/pps+4
        try:
            while time.monotonic()<deadline:
                if select.select([rx],[],[],0.05)[0]:
                    while True:
                        try: data=rx.recv(16)
                        except BlockingIOError: break
                        ident,dlc,payload=struct.unpack('=IB3x8s',data)
                        seq=struct.unpack('>I',payload[4:])[0]
                        if ident != canid or dlc!=8 or payload[:4]!=nonce or seq>=count: unexpected+=1
                        elif seq in seen: duplicates+=1
                        else: seen.add(seq)
                if done.is_set() and len(seen)>=count: break
        except Exception as e: recv_exception=repr(e)
    t=threading.Thread(target=receive);t.start();sent=0
    try:
        for i in range(count):
            target=start+i/pps
            delay=target-time.monotonic()
            if delay>0:time.sleep(delay)
            raw=struct.pack('=IB3x8s',canid,8,nonce+struct.pack('>I',i))
            deadline=time.monotonic()+0.2
            while True:
                try:tx.send(raw);sent+=1;break
                except (BlockingIOError,OSError) as e:
                    if getattr(e,'errno',None) not in (11,105) or time.monotonic()>deadline:raise
                    time.sleep(0.001)
    except Exception as e:send_exception=repr(e)
    finally:
        done.set(); t.join(timeout=count/pps+6);tx.close();rx.close()
    result={'direction':txname+' -> '+rxname,'kind':'extended' if canid&0x80000000 else 'standard','bitrate':1000000,'target_frames':count,'sent_frames':sent,'received_unique_frames':len(seen),'missing_frames':count-len(seen),'duplicate_frames':duplicates,'wrong_frames':unexpected,'elapsed_seconds':round(time.monotonic()-start,3),'target_frames_per_second':pps,'send_error':send_exception,'receive_error':recv_exception,'software_local_echo':False,'payload_nonce_hex':nonce.hex(),'can_id_hex':hex(canid)}
    result['pass']=sent==count and len(seen)==count and unexpected==0 and duplicates==0 and not send_exception and not recv_exception
    return result

def serial_direction(tx,rx,total,block=256):
    started=time.monotonic(); sent=received=wrong=local_echo=0; digest=hashlib.sha256();got_digest=hashlib.sha256(); issue=None
    nonce=os.urandom(32)
    try:
        tx.reset_input_buffer(); rx.reset_input_buffer()
        for offset in range(0,total,block):
            n=min(block,total-offset)
            data=bytes((offset+i)%256 for i in range(n)) if offset==0 else hashlib.shake_256(nonce+struct.pack('>I',offset)).digest(n)
            tx.reset_input_buffer(); rx.reset_input_buffer()
            wrote=tx.write(data);tx.flush(); sent+=wrote;digest.update(data[:wrote])
            got=bytearray();deadline=time.monotonic()+max(0.5,n*10/tx.baudrate+0.25)
            while len(got)<n and time.monotonic()<deadline:
                if select.select([rx.fileno()],[],[],min(0.05,max(0,deadline-time.monotonic())))[0]:got.extend(rx.read(n-len(got)))
            time.sleep(0.003)
            got.extend(rx.read(rx.in_waiting));received+=len(got); got_digest.update(got)
            local_echo+=tx.in_waiting
            if bytes(got)!=data:
                wrong+=1; issue={'offset':offset,'expected_length':n,'received_length':len(got),'mismatch_bytes':sum(a!=b for a,b in zip(got,data))}; break
    except Exception as e:issue=repr(e)
    return {'direction':tx.port+' -> '+rx.port,'baud':tx.baudrate,'format':'8N1','sent_bytes':sent,'received_bytes':received,'expected_bytes':total,'bad_blocks':wrong,'sender_echo_bytes':local_echo,'tx_sha256':digest.hexdigest(),'rx_sha256':got_digest.hexdigest(),'elapsed_seconds':round(time.monotonic()-started,3),'issue':issue,'pass':sent==total and received==total and wrong==0 and issue is None and digest.digest()==got_digest.digest()}
