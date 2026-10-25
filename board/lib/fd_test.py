# SPDX-License-Identifier: GPL-2.0-only
import hashlib,os,select,socket,struct,threading,time,json
def sock(n,ids):
    s=socket.socket(socket.PF_CAN,socket.SOCK_RAW,socket.CAN_RAW)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,2*1024*1024)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_LOOPBACK,0)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_RECV_OWN_MSGS,0)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_FD_FRAMES,1)
    s.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_FILTER,b''.join(struct.pack('=II',i,0xdfffffff) for i in ids))
    s.bind((n,));s.setblocking(False);return s

def transfer(txname,rxname,count,pps=2000,extended=False,lengths=(64,)):
    ident=(0x80000000|0x1ce00701 if extended else 0x601)+(txname=='can1')
    nonce=os.urandom(16);expected=[]
    for i in range(count):
        length=lengths[i%len(lengths)]
        payload=struct.pack('>I',i)+hashlib.shake_256(nonce+struct.pack('>I',i)).digest(max(0,length-4))
        expected.append(payload[:length])
    tx=sock(txname,[0x7fe]);rx=sock(rxname,[ident]);seen=set();missing=count;duplicates=wrong=unexpected_flags=0;sent=0;send_error=receive_error=None
    finished=threading.Event();start=time.monotonic();rxhash=hashlib.sha256();txhash=hashlib.sha256()
    def receive():
        nonlocal duplicates,wrong,unexpected_flags,receive_error
        deadline=start+count/pps+3
        try:
            while time.monotonic()<deadline:
                if select.select([rx],[],[],0.03)[0]:
                    while True:
                        try:raw,anc,flags,addr=rx.recvmsg(72)
                        except BlockingIOError:break
                        if len(raw)!=72:wrong+=1;continue
                        canid,length,fdflags,data=struct.unpack('=IBB2x64s',raw)
                        if flags&(socket.MSG_CONFIRM|socket.MSG_DONTROUTE) or not fdflags&1 or not fdflags&4:unexpected_flags+=1
                        seq=struct.unpack('>I',data[:4])[0]
                        if canid!=ident or seq>=count or length!=len(expected[seq]) or data[:length]!=expected[seq]:wrong+=1
                        elif seq in seen:duplicates+=1
                        else:seen.add(seq);rxhash.update(data[:length])
                if finished.is_set() and len(seen)==count:break
        except Exception as e:receive_error=repr(e)
    t=threading.Thread(target=receive);t.start()
    try:
        for i,data in enumerate(expected):
            delay=start+i/pps-time.monotonic()
            if delay>0:time.sleep(delay)
            raw=struct.pack('=IBB2x64s',ident,len(data),5,data)
            deadline=time.monotonic()+.2
            while True:
                try:tx.send(raw);sent+=1;txhash.update(data);break
                except (BlockingIOError,OSError) as e:
                    if getattr(e,'errno',None) not in (11,105) or time.monotonic()>deadline:raise
                    time.sleep(.001)
    except Exception as e:send_error=repr(e)
    finally:
        finished.set();t.join(timeout=count/pps+5);tx.close();rx.close()
    r={'direction':txname+' -> '+rxname,'nominal_bitrate':1000000,'data_bitrate':5000000,'BRS':True,'FD':True,'kind':'extended' if extended else 'standard','payload_lengths':list(lengths),'payload_nonce_hex':nonce.hex(),'can_id_hex':hex(ident),'target_frames':count,'sent_frames':sent,'received_unique_frames':len(seen),'missing_frames':count-len(seen),'duplicate_frames':duplicates,'wrong_frames':wrong,'invalid_fd_or_echo_flags':unexpected_flags,'tx_sha256':txhash.hexdigest(),'rx_sha256':rxhash.hexdigest(),'requested_frames_per_second':pps,'elapsed_seconds':round(time.monotonic()-start,3),'send_error':send_error,'receive_error':receive_error,'local_socket_echo':False}
    r['pass']=sent==count and len(seen)==count and duplicates==wrong==unexpected_flags==0 and not send_error and not receive_error and txhash.digest()==rxhash.digest()
    print(json.dumps(r),flush=True);return r
