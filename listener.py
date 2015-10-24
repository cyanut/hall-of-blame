#!/usr/bin/python
from __future__ import absolute_import, division, print_function, unicode_literals
import socket
#from multiprocessing import Process as Thread
from threading import Thread
from select import select
from trainer import process_game_packet
SRV_ADDR = "192.155.229.164"
PORT = 3336
TEST = False
data_worker = None


class Listener(object):


    def __init__(self, remote_addr, local_port, remote_port, q=None):
        self.remote_addr = remote_addr
        self.remote_port = remote_port
        self.local_port = local_port
        self.running = False
        self.q = q
        self.listening_socket = None
        self.local_connection = None
        self.remote_connection = None

    def serve(self):
        self.running = True
        
        local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        local_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        local_socket.bind(("", self.local_port))
        local_socket.listen(1)
        self.listening_socket = local_socket


        print("Server listening @ {} ...".format(self.local_port))

        #it seems the client connect twice: one for cross-domain policy, one 
        # for real
        while self.running:
            conn, addr = local_socket.accept()
            self.local_connection = conn
            print("{} connected {} !".format(addr, self.local_port))
            self.remote_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.remote_connection.connect((self.remote_addr, self.remote_port))
            print("{} connected to {}".format(self.remote_connection.getsockname(), (self.remote_addr, self.remote_port)))
            self.remote_connection.setblocking(1)
            self.remote_connection.setblocking(1)
            success_conn = manage_conn(self.local_connection, self.remote_connection, self.q)
            
            '''
            work_thread = threading.Thread(target=manage_conn, \
                                        args=(conn, srv_local_socket, q))
            work_thread.start()
            '''

    def stop(self):
        self.running = False
        print("sockets:", self.listening_socket, self.local_connection, self.remote_connection)
        if self.listening_socket:
            self.listening_socket.close()
        if self.local_connection:
            self.local_connection.close()
        if self.remote_connection:
            self.remote_connection.close()




def manage_conn(cli, srv, q):
    live = True
    eat_response = None
    return_status = True
    msg_buff = b""
    uname = None
    while live:
        rl, wl, el = select([cli, srv], [], [])
        for rs in rl:
            msg_raw = rs.recv(4096)
            #print("---raw---", repr(msg_raw))
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

                #print(source,"=>", repr(msg))
                target.send(msg + b"\x00")
                if q:
                    #login info
                    if msg.startswith(b"<sc_loginok"):
                        ind_uname = msg.find('user="') + 6
                        if ind_uname < 0:
                            continue
                        end_uname = msg[ind_uname:].index('"')
                        if end_uname < 0:
                            continue
                        uname = msg[ind_uname: ind_uname + end_uname]
                        print("selecting user name", uname)

                    if msg.startswith(b"<sc_board") and uname in msg:
                        data_worker = Thread(\
                                target = process_game_packet, 
                                args = (msg, q))
                        data_worker.start()
    return return_status




if __name__ == "__main__":
    listener = Listener(SRV_ADDR, PORT, PORT)
    listener.serve()
    

