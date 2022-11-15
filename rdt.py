from config import *
from FDFTPsocket import *
import socket
import struct
import os
import time
import math
import threading

class rdt:
    
    def __init__(self):
        '''create UDP socket'''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.temp_filepath = ''
    
    def make_pkt(self, length=MSS, seq=0, ack=0, isfin=0, issyn=0, data=' '.encode()):
        '''make transport layer packet'''
        return struct.pack('5i' + str(MSS) + 's', length, seq, ack, isfin, issyn, data)

    def extract(self, rcvpkt):
        '''extract transport layer packet'''
        return struct.unpack('5i' + str(MSS) + 's', rcvpkt)
    
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
        return self.socket.recvfrom(BUFSIZE)
    
    def __deliver_data(self):
        '''transport layer to application layer'''
        self.file.write(self.deliver_data)
        self.file.flush()
        
    def __send_msg_pkt(self, addr):
        '''sender: send packets inside cwnd, GBN if timeout'''
        while not self.disconnect:
            with self.lock:
                send_now = False
                # send all packets
                if self.PACKETS_NUM < self.send_base: 
                    break
                # fast retransmit
                if self.fast_retransmit:
                    self.fast_retransmit = False
                    send_now = True # fast retransmit
                    if DEBUG: print(f'FR')
                # timeout
                if CONG_TIMEOUT < (time.time() - self.timer):
                    self.ssthresh = max(float(math.floor(self.cwnd / 2)), 1.0)
                    self.cwnd = 1.0
                    self.nextseqnum = self.send_base
                    send_now = True # retransmit
                    self.timer = time.time()
                    if DEBUG: print(f'timeout  ssthresh={self.ssthresh}')
                # send packet
                if self.send_base <= self.nextseqnum and self.nextseqnum < self.send_base + int(self.cwnd) and self.nextseqnum <= self.PACKETS_NUM:
                    # buffer payload
                    if self.bufferedseqnum < self.nextseqnum:
                        if self.nextseqnum == self.PACKETS_NUM:
                            self.send_buffer.append(self.__rdt_send(self.LAST_PACKET_SIZE))
                        else:
                            self.send_buffer.append(self.__rdt_send(MSS))
                        self.bufferedseqnum = self.nextseqnum
                        send_now = True # new pkt
                    # send packet
                    if send_now:
                        payload = self.send_buffer[self.nextseqnum - self.send_base]
                        if self.nextseqnum == self.PACKETS_NUM:
                            sndpkt = self.make_pkt(length=self.LAST_PACKET_SIZE, seq=self.nextseqnum, isfin=1, data=payload)
                            if self.use_task:
                                self.task.sendto(self.socket, sndpkt, addr)
                            else:
                                self.udt_send(sndpkt, addr)
                            if self.nextseqnum > self.sended:
                                if DEBUG: print(f'send     seq={self.nextseqnum}, fin')
                                self.sended += 1
                            else:
                                if DEBUG: print(f'resend   seq={self.nextseqnum}, fin')
                                self.resend += 1
                        else:
                            sndpkt = self.make_pkt(seq=self.nextseqnum, data=payload)
                            if self.use_task:
                                self.task.sendto(self.socket, sndpkt, addr)
                            else:
                                self.udt_send(sndpkt, addr)
                            if self.nextseqnum > self.sended:
                                if DEBUG: print(f'send     seq={self.nextseqnum}, cwnd={self.cwnd}')
                                self.sended += 1
                            else:
                                if DEBUG: print(f'resend   seq={self.nextseqnum}, cwnd={self.cwnd}')
                                self.resend += 1
                    # move next
                    self.nextseqnum += 1

    def __receive_ack_pkt(self):
        '''sender: receive acks, shutdown if receive isfin'''
        try:
            while True:
                rcvpkt, addr = self.rdt_rcv()
                length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
                with self.lock:
                    if isfin == 0:
                        if DEBUG: print(f'receive  ack={ack}')
                        # fast retransmit
                        if self.send_base == ack + 1:
                            self.dulplicate_ack += 1
                            if self.dulplicate_ack == 3:
                                self.ssthresh = max(float(math.floor(self.cwnd / 2)), 1.0)
                                self.cwnd = self.ssthresh + 3.0
                                self.nextseqnum = self.send_base
                                self.fast_retransmit = True
                                self.timer = time.time()
                            if self.dulplicate_ack > 3:
                                self.cwnd += 1.0
                                if self.cwnd > RWND: 
                                    self.cwnd = float(RWND)
                                self.timer = time.time()
                        # recive confirming ack
                        if self.send_base <= ack:
                            # after fast retransmit but not partial ack
                            if self.dulplicate_ack >= 3 and not (ack < self.send_base + self.cwnd):
                                self.cwnd = self.ssthresh
                            self.dulplicate_ack = 1
                            gap = ack - self.send_base + 1
                            self.send_base = self.send_base + gap
                            self.nextseqnum = self.send_base
                            del self.send_buffer[0:gap]
                            self.timer = time.time()
                            for i in range(gap):
                                if self.cwnd < self.ssthresh:
                                    self.cwnd += 1.0
                                else:
                                    self.cwnd += 1.0 / self.cwnd
                                if self.cwnd > RWND: 
                                    self.cwnd = float(RWND)
                    else:
                        if DEBUG: print(f'receive  ack={ack}, finack')
                        self.send_base = self.PACKETS_NUM + 1 # terminate __send_msg_pkt
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
                        self.receive_acked[0] = True
                        self.receive_buffer[0] = data[:length]
                        # deliver sequence
                        if self.receive_acked.count(False) != 0:
                            deliver_num = self.receive_acked.index(False)
                        else:
                            deliver_num = len(self.receive_acked)
                        for i in range(deliver_num):
                            self.deliver_data = self.deliver_data + self.receive_buffer[0]
                            self.receive_buffer.pop(0)
                            self.receive_buffer.append(None)
                            self.receive_acked.pop(0)
                            self.receive_acked.append(False)
                        self.__deliver_data()
                        self.deliver_data = bytes()
                        if DEBUG: print(f'flush {deliver_num} pkts')
                        self.expectedseqnum += deliver_num
                    elif seq < self.expectedseqnum + RWND:
                        # buffer valid
                        if not self.receive_acked[seq - self.expectedseqnum]:
                            self.receive_acked[seq - self.expectedseqnum] = True
                            self.receive_buffer[seq - self.expectedseqnum] = data[:length]
                    ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.make_pkt(ack=ack, isfin=isfin)
                self.udt_send(sndpkt, addr)
                if DEBUG: print(f'send     ack={ack}')
            else:
                if DEBUG: print(f'receive  seq={seq}, fin')
                # update ack, buffer
                if seq < self.expectedseqnum:
                    isfin = 0
                    ack = seq
                elif seq == self.expectedseqnum:
                    if length != 0: # length == 0 means download empty file
                        self.deliver_data = self.deliver_data + data[:length]
                        self.__deliver_data()
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
                    if DEBUG: print(f'send     ack={ack}')
                else:
                    if DEBUG: print(f'send     ack={ack}, finack')
                    break
                
    def rdt_upload_file(self, source_path, addr, is_temp_file=False):
        '''client or server upload file'''
        # file
        if os.path.isfile(source_path): # open file
            self.file = open(source_path, 'rb')
            self.FILE_SIZE = os.path.getsize(source_path)
            self.PACKETS_NUM = self.FILE_SIZE // MSS + 1
            self.LAST_PACKET_SIZE = self.FILE_SIZE - (self.PACKETS_NUM - 1) * MSS
        else: # empty file
            self.PACKETS_NUM = 1
            self.LAST_PACKET_SIZE = 0
        # send msg
        self.send_buffer = []
        self.timer = time.time()
        self.send_base = 1
        self.nextseqnum = 1
        self.bufferedseqnum = 0
        self.sended = 0
        self.resend = 0
        # congestion control
        self.ssthresh = CONG_DEFALUT_SSTHRESH
        self.cwnd = 1.0
        self.dulplicate_ack = 1
        # semaphores and lock between 2 thead
        self.fast_retransmit = False # sem
        self.disconnect = False # sem
        self.lock = threading.Lock() # lock
        # send pkts and receive acks
        self.use_task = False
        if os.path.isfile(source_path) and not is_temp_file: # use task only if transfer valid file
            beg_time = time.time()
            self.use_task = True
            self.task = Task(source_path)
        send = threading.Thread(target=self.__send_msg_pkt, args=(addr, ))
        receive = threading.Thread(target=self.__receive_ack_pkt)
        send.start()
        receive.start()
        send.join()
        receive.join()
        if self.use_task:
            self.task.finish()
            end_time = time.time()
            transfer_time = end_time - beg_time
            file_size_KB = self.FILE_SIZE / math.pow(2, 10)
            transfer_rate = file_size_KB / transfer_time
            if self.resend + self.sended != 0:
                pkt_loss_rate = self.resend / (self.resend + self.sended) * 100
            else:
                pkt_loss_rate = 0
            if PERFORMANCE: 
                print(f'size={file_size_KB}Mb')
                print(f'time={transfer_time}s')
                print(f'rate={transfer_rate}Mbps')
                print(f'pkt_loss_rate={pkt_loss_rate}%')
        # close file if necessary
        if os.path.isfile(source_path): 
            self.file.close()
    
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
        self.receive_buffer = [None] * RWND
        self.receive_acked = [False] * RWND
        self.deliver_data = bytes()
        self.__receive_msg_pkt_and_send_ack_pkt(addr)
        # close file
        self.file.close()
        if os.path.getsize(dest_path) == 0:
            filename = dest_path[dest_path.find('/')+1:]
            os.remove(dest_path)

    def close(self):
        '''close socket and clear tempfile'''
        self.socket.close()
        try: self.file.close()
        except: pass
        try: os.remove(self.temp_filepath)
        except: pass
    