#!/usr/bin/python
from __future__ import absolute_import, division, print_function, unicode_literals
import socket
#from multiprocessing import Process as Thread
from threading import Thread
from select import select
from trainer import process_game_packet
SRV_ADDR = "192.155.229.163"
PORT = 3336
TEST = False




def serve(remote_addr, port, q=None):
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    skt.bind(("", port))
    skt.listen(1)

    print("Server listening @ " + str(port) + " ...")

    #it seems the client connect twice: one for cross-domain policy, one 
    # for real
    success_conn = False
    while not success_conn:
        conn, addr = skt.accept()
        print(repr(addr) + " connected " + str(port) + " !")
        srv_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_skt.connect((remote_addr, port))
        print(repr(srv_skt.getsockname()) + "connected to " + repr((remote_addr, port)))
        conn.setblocking(1)
        srv_skt.setblocking(1)
        success_conn = manage_conn(conn, srv_skt, q)
        
        '''
        work_thread = threading.Thread(target=manage_conn, \
                                    args=(conn, srv_skt, q))
        work_thread.start()
        '''

def manage_conn(cli, srv, q):
    live = True
    eat_response = None
    return_status = True
    msg_buff = b""
    while live:
        rl, wl, el = select([cli, srv], [], [])
        for rs in rl:
            msg_raw = rs.recv(4096)
            if not msg_raw:
                live = False
                continue
            msg_raw = b"".join([msg_buff, msg_raw])
            msgs = msg_raw.split(b"\x00")
            if len(msgs) == 1:
                msg_buff = msgs[0]
                msgs = []
            else:
                msg_buff = msgs[-1]
                msgs = msgs[:-1]
            for msg in msgs:
                if eat_response == rs:
                    eat_response = None
                    print("eating response: {}".format(msg))
                    continue
                if rs == cli:
                    if msg[:22] == b"<policy-file-request/>":
                        cli.send(b'<?xml version="1.0"?><!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd"><!-- Policy file for xmlsocket://socks.mysite.com --><cross-domain-policy><allow-access-from domain="*" to-ports="80-8999" /></cross-domain-policy>\x00')
                        eat_response = srv
                        return_status = False

                    target = srv
                    symbol = str(rs.getsockname()[1])+"==> "
                elif rs == srv:
                    symbol = "<== " + repr(rs.getpeername()) 
                    target = cli
                if rs == cli:
                    source = "C"
                else:
                    source = "S"

                print(source,"=>", msg)
                target.send(msg + b"\x00")
                if q:
                    if msg[:9] == b"<sc_board":
                        data_worker = Thread(\
                                target = process_game_packet, 
                                args = (msg, q))
                        data_worker.start()
    return return_status




if __name__ == "__main__":
    serve(SRV_ADDR, PORT)
    

