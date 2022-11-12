from config import *
import struct
import os
import socket
from threading import Thread
from time import *

class rdt:
    
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.file = open('client/temp.txt', 'w')
        self.file.close()
    
    def make_pkt(self, length=PACKET_SIZE, seq=0, ack=0, isfin=0, issyn=0, data=' '.encode()):
        return struct.pack("5i" + str(PACKET_SIZE) + "s", length, seq, ack, isfin, issyn, data)

    def extract(self, rcvpkt):
        return struct.unpack("5i" + str(PACKET_SIZE) + "s", rcvpkt)
    
    def rdt_send(self, size):
        return self.file.read(size)

    def udt_send(self, sndpkt, addr):
        self.socket.sendto(sndpkt, addr)

    def rdt_rcv(self):
        return self.socket.recvfrom(BUFFER_SIZE)
    
    def deliver_data(self, receive_buffer):
        self.file.write(receive_buffer)
        self.file.flush()
        
    def send_msg_pkt(self, addr):
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
                        self.send_buffer.append(self.rdt_send(self.LAST_PACKET_SIZE))
                    else:
                        self.send_buffer.append(self.rdt_send(PACKET_SIZE))
                    self.bufferedseqnum = self.nextseqnum
                # get payload
                payload = self.send_buffer[self.nextseqnum - self.send_base]
                # make packet
                if self.nextseqnum == self.PACKETS_NUM:
                    sndpkt = self.make_pkt(length=self.LAST_PACKET_SIZE, seq=self.nextseqnum, isfin=1, data=payload)
                    if self.nextseqnum > self.sended:
                        print("send     seq=" + str(self.nextseqnum) + ", fin")
                        self.sended += 1
                    else:
                        print("resend   seq=" + str(self.nextseqnum) + ", fin")
                else:
                    sndpkt = self.make_pkt(seq=self.nextseqnum, data=payload)
                    if self.nextseqnum > self.sended:
                        print("send     seq=" + str(self.nextseqnum) + ", cwnd=" + str(int(self.cwnd)))
                        self.sended += 1
                    else:
                        print("resend   seq=" + str(self.nextseqnum) + ", cwnd=" + str(int(self.cwnd)))
                # send packet
                self.udt_send(sndpkt, addr)
                # move next
                self.nextseqnum += 1

    def receive_ack_pkt(self):
        '''receive ack_pkt, adjust timer and cwnd and send_buffer, shutdown if receive isfin'''
        while True:
            rcvpkt, addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
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

    def receive_msg_pkt_and_send_ack_pkt(self, addr):
        '''receive packet and send ack, until the whole file is acked'''
        while True:
            # self.socket.settimeout(RCV_TIMEOUT) # in prevention of client offline
            rcvpkt, client_addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
            if isfin == 0:
                # update ack, expectedseqnum, buffer
                if seq == self.expectedseqnum:
                    self.receive_buffer = self.receive_buffer + data[:length]
                    self.buffer_count += 1
                    if RCV_BUFSIZE <= self.buffer_count:
                        self.deliver_data(self.receive_buffer)
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
                sndpkt = self.make_pkt(ack=ack, isfin=isfin)
                self.udt_send(sndpkt, addr)
                print("send     ack=" + str(ack))
            else:
                print("receive  fin")
                # update ack, buffer
                if seq == self.expectedseqnum:
                    self.receive_buffer = self.receive_buffer + data[:length]
                    self.buffer_count += 1
                    self.deliver_data(self.receive_buffer)
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
                sndpkt = self.make_pkt(ack=ack, isfin=isfin)
                self.udt_send(sndpkt, addr)
                if isfin == 0:
                    print("send     ack=" + str(ack))
                else:
                    print("send     ack=" + str(ack) + ", finack")
                    break
                
    def rdt_upload_file(self, source_path, addr):
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
        self.ssthresh = CONG_DEFALUT_SSTHRESH
        self.cwnd = 1.0
        send = Thread(target=self.send_msg_pkt, args=(addr, ))
        receive = Thread(target=self.receive_ack_pkt)
        send.start()
        receive.start()
        send.join()
        receive.join()
        # close file
        self.file.close()
    
    def rdt_download_file(self, dest_path, addr):
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
        self.receive_msg_pkt_and_send_ack_pkt(addr)
        # close file
        self.file.close()
