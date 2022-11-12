from config import *
import struct
import os
import socket
from time import *
from threading import Thread

class Server():

    def __make_pkt(self, length=PACKET_SIZE, seq=0, ack=0, isfin=0, issyn=0, isack=1, data=' '.encode()):
        return struct.pack("6i" + str(PACKET_SIZE) + "s", length, seq, ack, isfin, issyn, isack, data)

    def __extract(self, rcvpkt):
        return struct.unpack("6i" + str(PACKET_SIZE) + "s", rcvpkt)

    def __udt_send(self, sndpkt):
        self.socket.sendto(sndpkt, self.client_addr)
        
    def __rdt_rcv(self):
        rcvpkt, client_addr = self.socket.recvfrom(2048)
        return (rcvpkt, client_addr)
    
    def __deliver_data(self, receive_buffer):
        self.file.write(receive_buffer)
        self.file.flush()

    def __receive_msg_pkt_and_send_ack_pkt(self):
        '''receive packet and send ack, until the whole file is acked'''
        while True:
            # self.socket.settimeout(RCV_TIMEOUT) # in prevention of client offline
            rcvpkt, client_addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if isfin == 0:
                # update ack, expectedseqnum, buffer
                if seq == self.expectedseqnum:
                    self.receive_buffer = self.receive_buffer + data[:length]
                    self.buffer_count += 1
                    if BUFFER_SIZE <= self.buffer_count:
                        self.__deliver_data(self.receive_buffer)
                        self.receive_buffer = bytes()
                        self.buffer_count = 0
                        print("flush")
                    ack = self.expectedseqnum
                    self.expectedseqnum += 1
                else:
                    if seq < self.expectedseqnum:
                        ack = seq
                    else:
                        ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.__make_pkt(ack=ack, isfin=isfin)
                self.__udt_send(sndpkt)
                print("send     ack=" + str(ack))
            else:
                print("receive  fin")
                # update ack, buffer
                if seq == self.expectedseqnum:
                    self.receive_buffer = self.receive_buffer + data[:length]
                    self.buffer_count += 1
                    self.__deliver_data(self.receive_buffer)
                    self.receive_buffer = bytes()
                    self.buffer_count = 0
                    print("flush")
                    ack = self.expectedseqnum
                else:
                    isfin = 0
                    if seq < self.expectedseqnum:
                        ack = seq
                    else:
                        ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.__make_pkt(ack=ack, isfin=isfin)
                self.__udt_send(sndpkt)
                if isfin == 0:
                    print("send     ack=" + str(ack))
                else:
                    print("send     ack=" + str(ack) + ", finack")
                    break
    
    def __init__(self, port):
        '''create socket'''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', port))
        # only used by welcome_socket
        self.connection_port = int(SERVER_PORT) + 1
        
    def accept(self):
        '''welcome socket: 3 handshakes and prepare connection_socket'''
        # 3 handshakes
        while True:
            success = False
            # handshake 1
            rcvpkt, client_addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if (issyn != 1) or (seq != 1): continue
            # handshake 2
            self.client_addr = client_addr
            connection_port = str(self.connection_port)
            sndpkt = self.__make_pkt(length=len(connection_port), issyn=1, data=connection_port.encode())
            self.__udt_send(sndpkt)
            # handshake 3
            re_rcvpkt, re_addr = self.__rdt_rcv()
            re_length, re_seq, re_ack, re_isfin, re_issyn, re_isack, re_data = self.__extract(re_rcvpkt)
            if (re_issyn != 1) or (re_seq != 2) or (client_addr != re_addr): continue
            break
        # prepare connection socket
        self.connection_port += 1
        return (self.connection_port - 1, client_addr)
    
    def connect(self, client_addr):
        '''connection socket: connect client'''
        self.client_addr = client_addr
    
    def rdt_receive(self):
        '''connection socket: rdt receive filename and file'''
        for i in range(2):
            # get dest_path
            if i == 0: # save filename
                dest_path = 'server/temp.txt'
            else: # recieve file
                self.file = open('server/temp.txt', 'r')
                dest_path = 'server/' + self.file.read()
                self.file.close()
            # clear old file
            try: os.remove(dest_path)
            except: pass
            # create file
            self.file = open(dest_path, 'w')
            self.file.close()
            # open file and receive
            self.file = open(dest_path, 'wb')
            self.receive_buffer = bytes()
            self.buffer_count = 0
            self.expectedseqnum = 1
            self.__receive_msg_pkt_and_send_ack_pkt()
            # close file
            self.file.close()

    def close(self):
        '''close socket'''
        self.socket.close()

def communicate(connection_port, client_addr):
    '''connection socket thread'''
    connection_socket = Server(connection_port)
    connection_socket.connect(client_addr)
    try:
        while True: # receive 1 file each time
            connection_socket.rdt_receive()
    except Exception as e:
        connection_socket.close()
        print(str(e))

def main():
    # welcome socket
    welcome_socket = Server(SERVER_PORT)
    # listen
    try:
        while True:
            # 3 handshakes
            connection_port, client_addr = welcome_socket.accept()
            # connection socket works
            connection = Thread(target=communicate, args=(connection_port, client_addr))
            connection.start()
    except Exception as e:
        welcome_socket.close()
        print(str(e))

if __name__ == "__main__":
    main()
