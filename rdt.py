from config import *
import struct
import os
import socket
from threading import Thread
from time import *

class rdt:
    
    def __init__(self):
        '''create UDP socket'''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.temp_filepath = ''
    
    def make_pkt(self, length=PACKET_SIZE, seq=0, ack=0, isfin=0, issyn=0, data=' '.encode()):
        '''make transport layer packet'''
        return struct.pack('5i' + str(PACKET_SIZE) + 's', length, seq, ack, isfin, issyn, data)

    def extract(self, rcvpkt):
        '''extract transport layer packet'''
        return struct.unpack('5i' + str(PACKET_SIZE) + 's', rcvpkt)
    
    def __rdt_send(self, size):
        '''application layer to transport layer'''
        if size == 0:
            return ' '.encode()
        else:
            return self.file.read(size)

    def udt_send(self, sndpkt, addr):
        '''transport layer to network layer'''
        self.socket.sendto(sndpkt, addr)

    def rdt_rcv(self):
        '''network layer to transport layer'''
        return self.socket.recvfrom(BUFFER_SIZE)
    
    def __deliver_data(self):
        '''transport layer to application layer'''
        self.file.write(self.deliver_data)
        
    def __send_msg_pkt(self, addr):
        '''sender: send packets inside cwnd, GBN if timeout'''
        while not self.disconnect:
            # pop
            gap = self.send_base - self.old_base
            if gap > 0:
                for i in range(gap):
                    self.send_buffer.pop(0)
                self.old_base = self.old_base + gap
            # send all packets
            if self.PACKETS_NUM < self.old_base: break
            # timeout
            if CONG_TIMEOUT < (time() - self.timer):
                self.nextseqnum = self.old_base
                self.ssthresh = float(int(self.cwnd) // 2)
                if self.ssthresh < 1.0:
                    self.ssthresh = 1.0
                self.cwnd = 1.0
                self.timer = time()
                # self.resend += 1
                if DEBUG: print('timeout  ssthresh=' + str(int(self.ssthresh)))
            # send packet
            if self.nextseqnum <= self.PACKETS_NUM and self.old_base <= self.nextseqnum and self.nextseqnum < self.old_base + int(self.cwnd):
                # buffer payload
                flag = False
                if self.bufferedseqnum < self.nextseqnum:
                    if self.nextseqnum == self.PACKETS_NUM:
                        self.send_buffer.append(self.__rdt_send(self.LAST_PACKET_SIZE))
                    else:
                        self.send_buffer.append(self.__rdt_send(PACKET_SIZE))
                    self.bufferedseqnum = self.nextseqnum
                    flag = True
                # send packet
                if self.nextseqnum == self.old_base or flag:
                    payload = self.send_buffer[self.nextseqnum - self.old_base]
                    if self.nextseqnum == self.PACKETS_NUM:
                        sndpkt = self.make_pkt(length=self.LAST_PACKET_SIZE, seq=self.nextseqnum, isfin=1, data=payload)
                        self.udt_send(sndpkt, addr)
                        if self.nextseqnum > self.sended:
                            if DEBUG: print('send     seq=' + str(self.nextseqnum) + ', fin')
                            self.sended += 1
                        else:
                            if DEBUG: print('resend   seq=' + str(self.nextseqnum) + ', fin')
                            self.resend += 1
                    else:
                        sndpkt = self.make_pkt(seq=self.nextseqnum, data=payload)
                        self.udt_send(sndpkt, addr)
                        if self.nextseqnum > self.sended:
                            if DEBUG: print('send     seq=' + str(self.nextseqnum) + ', cwnd=' + str(int(self.cwnd)))
                            self.sended += 1
                        else:
                            if DEBUG: print('resend   seq=' + str(self.nextseqnum) + ', cwnd=' + str(int(self.cwnd)))
                            self.resend += 1
                # move next
                self.nextseqnum += 1

    def __receive_ack_pkt(self):
        '''sender: receive acks, shutdown if receive isfin'''
        try:
            while True:
                rcvpkt, addr = self.rdt_rcv()
                length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
                if isfin == 0:
                    if DEBUG: print('receive  ack=' + str(ack))
                    if self.send_base == ack + 1:
                        self.dul_ack += 1
                        if self.dul_ack == 3:
                            self.timer = time()
                            self.ssthresh = float(int(self.cwnd) // 2)
                            if self.ssthresh < 1.0:
                                self.ssthresh = 1.0
                            self.cwnd = int(self.ssthresh) + 3
                            self.nextseqnum = self.old_base
                            if DEBUG: print(f'FR       seq={self.nextseqnum}, cwnd={self.cwnd}')
                        if self.dul_ack > 3:
                            self.timer = time()
                            self.cwnd += 1
                    if self.send_base <= ack:
                        if self.dul_ack >= 3:
                            self.cwnd = int(self.ssthresh)
                        self.dul_ack = 1
                        gap = ack - self.send_base + 1
                        self.send_base = self.send_base + gap
                        self.timer = time()
                        if self.cwnd < self.ssthresh:
                            self.cwnd += 1.0 * gap
                        else:
                            self.cwnd += 1 / float(int(self.cwnd)) * gap
                else:
                    if DEBUG: print('receive  ack=' + str(ack) + ', finack')
                    self.send_base = self.PACKETS_NUM + 1
                    break
        except: # hint other thread to end
            self.disconnect = True
            
    def __receive_msg_pkt_and_send_ack_pkt(self, addr):
        '''receiver: receive packet and send ack, until the whole file is acked, send fin and wait for finack'''
        while True:
            rcvpkt, client_addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
            if isfin == 0:
                # update ack, expectedseqnum, buffer
                if seq < self.expectedseqnum:
                    ack = seq
                else:
                    if seq == self.expectedseqnum:
                        # buffer it
                        self.rack[0] = True
                        self.rbuf[0] = data[:length]
                        # deliver sequence
                        if self.rack.count(False) != 0:
                            deliver_num = self.rack.index(False)
                        else:
                            deliver_num = len(self.rack)
                        for i in range(deliver_num):
                            self.deliver_data = self.deliver_data + self.rbuf[0]
                            self.rbuf.pop(0)
                            self.rbuf.append(None)
                            self.rack.pop(0)
                            self.rack.append(False)
                        self.__deliver_data()
                        self.deliver_data = bytes()
                        if DEBUG: print(f'flush {deliver_num} pkts')
                        self.expectedseqnum += deliver_num
                    elif seq < self.expectedseqnum + RCV_BUFSIZE:
                        # buffer valid
                        if not self.rack[seq - self.expectedseqnum]:
                            self.rack[seq - self.expectedseqnum] = True
                            self.rbuf[seq - self.expectedseqnum] = data[:length]
                    else:
                        pass
                    ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.make_pkt(ack=ack, isfin=isfin)
                self.udt_send(sndpkt, addr)
                if DEBUG: print('send     ack=' + str(ack))
            else:
                if DEBUG: print('receive  seq=' + str(seq) + ', fin')
                # update ack, buffer
                if seq < self.expectedseqnum:
                    isfin = 0
                    ack = seq
                elif seq == self.expectedseqnum:
                    if length != 0: # length == 0 means download empty file
                        self.deliver_data = self.deliver_data + data[:length]
                        self.__deliver_data()
                        self.file.flush()
                        self.deliver_data = bytes()
                        if DEBUG: print('flush remaining pkts')
                    ack = self.expectedseqnum
                else:
                    isfin = 0
                    ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.make_pkt(ack=ack, isfin=isfin)
                self.udt_send(sndpkt, addr)
                if isfin == 0:
                    if DEBUG: print('send     ack=' + str(ack))
                else:
                    if DEBUG: print('send     ack=' + str(ack) + ', finack')
                    break
                
    def rdt_upload_file(self, source_path, addr):
        '''client or server upload file'''
        # init params
        if os.path.isfile(source_path): # open file
            self.file = open(source_path, 'rb')
            self.FILE_SIZE = os.path.getsize(source_path)
            self.PACKETS_NUM = self.FILE_SIZE // PACKET_SIZE + 1
            self.LAST_PACKET_SIZE = self.FILE_SIZE - (self.PACKETS_NUM - 1) * PACKET_SIZE
        else: # empty file
            self.PACKETS_NUM = 1
            self.LAST_PACKET_SIZE = 0
        self.send_buffer = []
        self.timer = time()
        self.send_base = 1
        self.old_base = 1
        self.nextseqnum = 1
        self.bufferedseqnum = 0
        self.sended = 0
        self.resend = 0
        self.ssthresh = CONG_DEFALUT_SSTHRESH
        self.cwnd = 1.0
        self.dul_ack = 1
        self.disconnect = False
        # send pkts and receive acks
        send = Thread(target=self.__send_msg_pkt, args=(addr, ))
        receive = Thread(target=self.__receive_ack_pkt)
        send.start()
        receive.start()
        send.join()
        receive.join()
        # close file if necessary
        if os.path.isfile(source_path): 
            self.file.close()
        # calc loss pkt rate
        if self.resend + self.sended != 0:
            return self.sended / (self.resend + self.sended)
        else:
            return 0
    
    def rdt_download_file(self, dest_path, addr):
        '''client or server download file'''
        # clear old file
        if os.path.isfile(dest_path): 
            os.remove(dest_path)
        # create file
        self.file = open(dest_path, 'w')
        self.file.close()
        # open file and receive
        self.file = open(dest_path, 'wb')
        self.expectedseqnum = 1
        self.rbuf = [None] * RCV_BUFSIZE
        self.rack = [False] * RCV_BUFSIZE
        self.deliver_data = bytes()
        self.__receive_msg_pkt_and_send_ack_pkt(addr)
        # close file
        self.file.close()
        if os.path.getsize(dest_path) == 0:
            print('file not exists')
            os.remove(dest_path)

    def close(self):
        '''close socket and clear tempfile'''
        self.socket.close()
        try: self.file.close()
        except: pass
        try: os.remove(self.temp_filepath)
        except: pass
    