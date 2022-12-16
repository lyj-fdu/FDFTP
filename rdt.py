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
        self.timeout = DEFAULT_CONG_TIMEOUT
        self.rwnd = DEFAULT_RWND
        self.temp_filepath = ''
        self.transaction_no = 0
    
    def make_pkt(self, length=MSS, seq=0, ack=0, isfin=0, issyn=0, txno=-666, data=' '.encode()):
        '''make transport layer packet'''
        if txno == -666:
            txno = self.transaction_no
        return struct.pack('6i' + str(MSS) + 's', length, seq, ack, isfin, issyn, txno, data)

    def extract(self, rcvpkt):
        '''extract transport layer packet'''
        return struct.unpack('6i' + str(MSS) + 's', rcvpkt)
    
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
                urgent = False
                window_size = min(int(self.cwnd), int(self.rwnd))
                # send all packets
                if self.PACKETS_NUM < self.send_base: 
                    break
                # timeout
                if self.timeout < (time.time() - self.timer):
                    urgent = True
                    self.measure_rtt = False
                    self.dulplicate_ack = 0
                    self.ssthresh = max(float(math.floor(self.cwnd / 2)), DEFAULT_CWND)
                    self.cwnd = DEFAULT_CWND
                    self.send_state = 'SS'
                    self.nextseqnum = self.send_base
                    self.send_now = True # retransmit
                    self.timer = time.time()
                    self.timeout *= 2
                    if DEBUG: print(f'timeout={self.timeout} ssthresh={self.ssthresh}')
                # send packet
                while self.send_base <= self.nextseqnum and self.nextseqnum < self.send_base + window_size and self.nextseqnum <= self.PACKETS_NUM:
                    # buffer payload
                    if self.bufferedseqnum < self.nextseqnum:
                        if self.nextseqnum == self.PACKETS_NUM:
                            self.send_buffer.append(self.__rdt_send(self.LAST_PACKET_SIZE))
                        else:
                            self.send_buffer.append(self.__rdt_send(MSS))
                        self.bufferedseqnum = self.nextseqnum
                        self.send_now = True # new pkt
                    # send packet
                    if self.send_now or urgent:
                        payload = self.send_buffer[self.nextseqnum - self.send_base]
                        if self.nextseqnum == self.PACKETS_NUM:
                            sndpkt = self.make_pkt(length=self.LAST_PACKET_SIZE, seq=self.nextseqnum, isfin=1, data=payload)
                            if self.use_task:
                                self.task.sendto(self.socket, sndpkt, addr)
                            else:
                                self.udt_send(sndpkt, addr)
                            if self.nextseqnum > self.sended:
                                if DEBUG: print(f'[{self.send_state}] send   seq={self.nextseqnum} <fin>')
                                self.sended += 1
                            else:
                                if DEBUG: print(f'[{self.send_state}] resend seq={self.nextseqnum} <fin>')
                                self.resend += 1
                        else:
                            sndpkt = self.make_pkt(seq=self.nextseqnum, data=payload)
                            if self.use_task:
                                self.task.sendto(self.socket, sndpkt, addr)
                            else:
                                self.udt_send(sndpkt, addr)
                            if self.nextseqnum > self.sended:
                                if DEBUG: print(f'[{self.send_state}] send   seq={self.nextseqnum}, cwnd={self.cwnd}')
                                self.sended += 1
                                if self.sended % 100 == 0:
                                    self.rtt_target_seq = self.sended
                                    self.measure_rtt = True
                                    self.rtt_start = time.time()
                            else:
                                if DEBUG: print(f'[{self.send_state}] resend seq={self.nextseqnum}, cwnd={self.cwnd}')
                                self.resend += 1
                        self.send_now = False # cancel next
                    # move next
                    self.nextseqnum += 1

    def __receive_ack_pkt(self):
        '''sender: receive acks, shutdown if receive isfin'''
        try:
            while True:
                rcvpkt, addr = self.rdt_rcv()
                length, seq, ack, isfin, issyn, txno, data = self.extract(rcvpkt)
                with self.lock:
                    if txno != self.transaction_no:
                        if DEBUG: print(f'discard txno={txno}, ack={seq}')
                        continue
                    if isfin == 0:
                        if DEBUG: print(f'receive ack={ack}')
                        # invalid ack
                        if ack < self.send_base - 1:
                            pass
                        # dulplicate ack
                        elif ack == self.send_base - 1:
                            self.dulplicate_ack += 1
                            if self.dulplicate_ack == 3:
                                self.measure_rtt = False
                                self.ssthresh = max(float(math.floor(self.cwnd / 2)), DEFAULT_CWND)
                                self.cwnd = self.ssthresh + 3.0
                                self.send_state = 'FR'
                                self.nextseqnum = self.send_base
                                self.send_now = True # fast_retransmit
                                self.timer = time.time()
                                self.timeout = self.timeout_interval
                            if self.dulplicate_ack > 3:
                                self.cwnd += 1.0
                                self.timer = time.time()
                                self.timeout = self.timeout_interval
                        # valid ack
                        else:
                            # dynamic measure rtt
                            if self.measure_rtt and self.rtt_target_seq == ack:
                                sample_rtt = time.time() - self.rtt_start
                                self.estimate_rtt = (1 - 0.125) * self.estimate_rtt + 0.125 * sample_rtt
                                self.dev_rtt = (1 - 0.25) * self.dev_rtt + 0.25 * abs(sample_rtt - self.estimate_rtt)
                                self.timeout_interval = self.estimate_rtt + 4 * self.dev_rtt
                                self.rwnd = math.floor(MAX_BANDWIDTH_Mbps * 1000000 * self.timeout_interval / 8 / MSS)
                                if DYNAMIC: print(f'seq={self.rtt_target_seq} timeout={self.timeout_interval} rwnd={self.rwnd}')
                                self.measure_rtt = False
                            # back to CA from FR
                            if self.send_state == 'FR':
                                self.cwnd = self.ssthresh
                                self.send_state = 'CA'
                            # adjust sender
                            self.dulplicate_ack = 0
                            gap = ack - self.send_base + 1
                            self.send_base = self.send_base + gap
                            self.nextseqnum = self.send_base
                            del self.send_buffer[0:gap]
                            for i in range(gap):
                                if self.send_state == 'CA':
                                    self.cwnd += 1.0 / self.cwnd
                                elif self.send_state == 'SS':
                                    self.cwnd += 1.0
                                    if self.cwnd > self.ssthresh:
                                        self.send_state = 'CA'
                            self.timer = time.time()
                            self.timeout = self.timeout_interval
                    else:
                        if DEBUG: print(f'receive ack={ack} <finack>')
                        self.send_base = self.PACKETS_NUM + 1 # terminate __send_msg_pkt
                        break
        except: # hint other thread to end
            self.disconnect = True
            
    def __receive_msg_pkt_and_send_ack_pkt(self, addr):
        '''receiver: receive packet and send ack, until the whole file is acked, send fin and wait for finack'''
        while True:
            rcvpkt, client_addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, txno, data = self.extract(rcvpkt)
            if txno != self.transaction_no:
                if DEBUG: print(f'discard txno={txno}, seq={seq}\nsend <fin>')
                sndpkt = self.make_pkt(isfin=1, txno=txno)
                self.udt_send(sndpkt, addr)
                continue
            if isfin == 0:
                if DEBUG: print(f'receive seq={seq}')
                # update ack, expectedseqnum, buffer
                if seq < self.expectedseqnum + self.rwnd:
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
                                self.deliver_count += 1
                                self.deliver_data = self.deliver_data + self.receive_buffer[0]
                                if self.deliver_count == WRITE_MAX:
                                    self.__deliver_data()
                                    self.deliver_count = 0
                                    self.deliver_data = bytes()
                                self.receive_buffer.pop(0)
                                self.receive_buffer.append(None)
                                self.receive_acked.pop(0)
                                self.receive_acked.append(False)
                            self.__deliver_data()
                            self.deliver_data = bytes()
                            if DEBUG: print(f'flush {deliver_num} pkts')
                            self.expectedseqnum += deliver_num
                        else:
                            # buffer valid
                            if not self.receive_acked[seq - self.expectedseqnum]:
                                self.receive_acked[seq - self.expectedseqnum] = True
                                self.receive_buffer[seq - self.expectedseqnum] = data[:length]
                        ack = self.expectedseqnum - 1
                    # send ack packet
                    sndpkt = self.make_pkt(ack=ack, isfin=isfin)
                    self.udt_send(sndpkt, addr)
                    if DEBUG: print(f'send    ack={ack}')
            else:
                if DEBUG: print(f'receive seq={seq} <fin>')
                # update ack, buffer
                if seq < self.expectedseqnum + self.rwnd:
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
                        if DEBUG: print(f'send    ack={ack}')
                    else:
                        if DEBUG: print(f'send    ack={ack} <finack>')
                        break
                
    def rdt_upload_file(self, source_path, addr, is_temp_file=False):
        '''client or server upload file'''
        self.transaction_no += 1
        if DEBUG: print(f'<txno={self.transaction_no}>')
        # file
        if os.path.isfile(source_path): # open file
            self.file = open(source_path, 'rb')
            self.FILE_SIZE = os.path.getsize(source_path)
            self.PACKETS_NUM = self.FILE_SIZE // MSS + 1
            self.LAST_PACKET_SIZE = self.FILE_SIZE - (self.PACKETS_NUM - 1) * MSS
        else: # empty file
            self.PACKETS_NUM = 1
            self.LAST_PACKET_SIZE = 0
        # send controls
        self.send_buffer = []
        self.timer = time.time()
        self.send_base = 1
        self.nextseqnum = 1
        self.send_now = False
        self.bufferedseqnum = 0
        self.sended = 0
        self.resend = 0
        # congestion controls
        self.ssthresh = self.rwnd
        self.cwnd = DEFAULT_CWND
        self.dulplicate_ack = 0
        self.send_state = 'SS'
        self.measure_rtt = False
        self.rtt_start = 0
        self.rtt_target_seq = 0
        self.estimate_rtt = self.timeout
        self.dev_rtt = 0
        self.timeout_interval = self.timeout
        # semaphores and lock between 2 thead
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
        # performance records
        if self.use_task:
            print('======')
            self.task.finish()
            end_time = time.time()
            transfer_time_s = end_time - beg_time
            file_size_Kb = self.FILE_SIZE / math.pow(2, 10)
            transfer_rate_Kbps = file_size_Kb / transfer_time_s
            if self.resend + self.sended != 0:
                pkt_loss_rate = self.resend / (self.resend + self.sended) * 100
            else:
                pkt_loss_rate = 0
            if PERFORMANCE: 
                print(f'size={file_size_Kb}Kb')
                print(f'time={transfer_time_s}s')
                print(f'rate={transfer_rate_Kbps}Kbps')
                print(f'pkt_loss_rate={pkt_loss_rate}%')
            print('======')
        # close file if necessary
        if os.path.isfile(source_path): 
            self.file.close()
    
    def rdt_download_file(self, dest_path, addr):
        '''client or server download file'''
        self.transaction_no += 1
        if DEBUG: print(f'<txno={self.transaction_no}>')
        # remove file
        if os.path.isfile(dest_path): 
            os.remove(dest_path)
        # create file
        self.file = open(dest_path, 'w')
        self.file.close()
        # open file
        self.file = open(dest_path, 'wb')
        # receive controls
        self.expectedseqnum = 1
        self.receive_buffer = [None] * DEFAULT_RWND
        self.receive_acked = [False] * DEFAULT_RWND
        self.deliver_count = 0
        self.deliver_data = bytes()
        # receive pkts and send acks
        self.__receive_msg_pkt_and_send_ack_pkt(addr)
        # close file
        self.file.close()
        # remove file if necessary
        if os.path.getsize(dest_path) == 0:
            os.remove(dest_path)
        
    def close(self):
        '''close socket and clear tempfile'''
        self.socket.close()
        try: self.file.close()
        except: pass
        try: os.remove(self.temp_filepath)
        except: pass
    