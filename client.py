from config import *
import struct
import os
import socket
from threading import Thread
from time import *

class Client:

    def __make_pkt(self, length=PACKET_SIZE, seq=0, ack=0, isfin=0, issyn=0, isack=0, data=' '.encode()):
        return struct.pack("6i" + str(PACKET_SIZE) + "s", length, seq, ack, isfin, issyn, isack, data)

    def __extract(self, rcvpkt):
        return struct.unpack("6i" + str(PACKET_SIZE) + "s", rcvpkt)
    
    def __rdt_send(self, size):
        return self.file.read(size)

    def __udt_send(self, sndpkt):
        self.socket.sendto(sndpkt, (self.server_ip, self.server_port))

    def __rdt_rcv(self):
        return self.socket.recvfrom(2048)
    
    def __send_msg_pkt(self):
        '''send packets inside cwnd, GBN if timeout'''
        while True:
            # send all packets
            if self.PACKETS_NUM < self.send_base: break
            # timeout
            if CONG_TIMEOUT < (time() - self.timer):
                self.nextseqnum = self.send_base
                self.ssthresh = float(int(self.cwnd) // 2)
                if self.ssthresh < 1.0:
                    self.ssthresh = 1.0
                self.cwnd = 1.0
                self.timer = time()
                print("timeout! ssthresh=" + str(int(self.ssthresh)))
            # send packet
            if self.nextseqnum <= self.PACKETS_NUM and self.nextseqnum < self.send_base + int(self.cwnd):
                # buffer payload
                if self.bufferedseqnum < self.nextseqnum:
                    if self.nextseqnum == self.PACKETS_NUM:
                        self.send_buffer.append(self.__rdt_send(self.LAST_PACKET_SIZE))
                    else:
                        self.send_buffer.append(self.__rdt_send(PACKET_SIZE))
                    self.bufferedseqnum = self.nextseqnum
                # get payload
                payload = self.send_buffer[self.nextseqnum - self.send_base]
                # make packet
                if self.nextseqnum == self.PACKETS_NUM:
                    sndpkt = self.__make_pkt(length=self.LAST_PACKET_SIZE, seq=self.nextseqnum, isfin=1, data=payload)
                    if self.nextseqnum > self.sended:
                        print("send     seq=" + str(self.nextseqnum) + ", fin")
                        self.sended += 1
                    else:
                        print("resend   seq=" + str(self.nextseqnum) + ", fin")
                else:
                    sndpkt = self.__make_pkt(seq=self.nextseqnum, data=payload)
                    if self.nextseqnum > self.sended:
                        print("send     seq=" + str(self.nextseqnum) + ", cwnd=" + str(int(self.cwnd)))
                        self.sended += 1
                    else:
                        print("resend   seq=" + str(self.nextseqnum) + ", cwnd=" + str(int(self.cwnd)))
                # send packet
                self.__udt_send(sndpkt)
                # move next
                self.nextseqnum += 1

    def __receive_ack_pkt(self):
        '''receive ack_pkt, adjust timer and cwnd and send_buffer, shutdown if receive isfin'''
        while True:
            rcvpkt, addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if isfin == 0:
                print("receive  ack=" + str(ack))
                if ack == self.send_base:
                    self.send_buffer.pop(0)
                    self.timer = time()
                    self.send_base = ack + 1
                    if self.cwnd < self.ssthresh:
                        self.cwnd += 1.0
                    else:
                        self.cwnd += 1 / float(int(self.cwnd))
            else:
                print("receive  ack=" + str(ack) + ", finack")
                self.send_base = self.PACKETS_NUM + 1
                break

    def __init__(self):
        '''create socket'''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def connect(self, server_ip=SERVER_IP, server_port=SERVER_PORT):
        '''handshake with welcome_socket and get server_port'''
        self.server_ip = server_ip
        self.server_port = server_port
        while True:
            # handshake 1
            sndpkt = self.__make_pkt(seq=1,issyn=1)
            self.__udt_send(sndpkt)
            # handshake 2
            rcvpkt, addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if not issyn: continue
            # handshake 3
            re_sndpkt = self.__make_pkt(seq=2,issyn=1)
            self.__udt_send(re_sndpkt)
            # get server_port
            self.server_port = int(data.decode()[:length])
            break

    def rdt_send(self, filename):
        '''rdt send filename and file'''
        print('====== ' + filename + ' ======')
        for i in range(2):
            # get source_path
            if i == 0: # send filename
                self.file = open('client/temp.txt', 'w')
                self.file.write(filename[filename.index('/')+1:])
                self.file.close()
                source_path = 'client/temp.txt'
            else: # send file
                source_path = filename
            # open file and send
            self.file = open(source_path, 'rb')
            self.FILE_SIZE = os.path.getsize(source_path)
            self.PACKETS_NUM = self.FILE_SIZE // PACKET_SIZE + 1
            self.LAST_PACKET_SIZE = self.FILE_SIZE - (self.PACKETS_NUM - 1) * PACKET_SIZE
            self.send_buffer = []
            self.timer = time()
            self.send_base = 1
            self.nextseqnum = 1
            self.bufferedseqnum = 0
            self.sended = 0
            self.ssthresh = DEFALUT_THRESHOLD
            self.cwnd = 1.0
            send = Thread(target=self.__send_msg_pkt)
            receive = Thread(target=self.__receive_ack_pkt)
            send.start()
            receive.start()
            send.join()
            receive.join()
            # close file
            self.file.close()
        # sleep(5)
            
    def close(self):
        '''close socket'''
        self.socket.close()

def main():
    # client socket
    client_socket = Client()
    # 3 handshakes and connect
    client_socket.connect(SERVER_IP, SERVER_PORT)
    # send files
    while True:
        filename = input('please input relative file path, or input nothing to exit:)\n')
        if filename == '': break
        client_socket.rdt_send(filename)
    # close client socket
    client_socket.close()

if __name__ == "__main__":
    main()
